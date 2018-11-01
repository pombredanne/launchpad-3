# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database access layer for the Librarian."""

__metaclass__ = type
__all__ = [
    'Library',
    ]

import hashlib
import urllib

from pymacaroons import Macaroon
from six.moves.xmlrpc_client import Fault
from storm.expr import (
    And,
    SQL,
    )
from twisted.internet import (
    defer,
    reactor as default_reactor,
    threads,
    )
from twisted.web import xmlrpc

from lp.services.config import config
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import session_store
from lp.services.librarian.model import (
    LibraryFileAlias,
    LibraryFileContent,
    TimeLimitedToken,
    )
from lp.services.twistedsupport import cancel_on_timeout
from lp.xmlrpc import faults


class Library:
    """Class that encapsulates the database interface for the librarian."""

    def __init__(self, restricted=False):
        """Create a new database access object.

        :param restricted: If this is set to true, only restricted
            will be served. Otherwise only public files will be served.
            Files created in this library will marked as restricted.
        """
        self.restricted = restricted
        self._authserver = xmlrpc.Proxy(
            config.librarian.authentication_endpoint,
            connectTimeout=config.librarian.authentication_timeout)

    # The following methods are read-only queries.

    def lookupBySHA1(self, digest):
        return [fc.id for fc in LibraryFileContent.selectBy(sha1=digest)]

    @defer.inlineCallbacks
    def _verifyMacaroon(self, macaroon, aliasid):
        """Verify an LFA-authorising macaroon with the authserver.

        This must be called in the reactor thread.

        :param macaroon: A `Macaroon`.
        :param aliasid: A `LibraryFileAlias` ID.
        :return: True if the authserver reports that `macaroon` authorises
            access to `aliasid`; False if it reports that it does not.
        :raises Fault: if the authserver request fails.
        """
        try:
            yield cancel_on_timeout(
                self._authserver.callRemote(
                    "verifyMacaroon", macaroon.serialize(), aliasid),
                config.librarian.authentication_timeout)
            defer.returnValue(True)
        except Fault as fault:
            if fault.faultCode == faults.Unauthorized.error_code:
                defer.returnValue(False)
            else:
                raise

    def getAlias(self, aliasid, token, path):
        """Returns a LibraryFileAlias, or raises LookupError.

        A LookupError is raised if no record with the given ID exists
        or if not related LibraryFileContent exists.

        :param aliasid: A `LibraryFileAlias` ID.
        :param token: The token for the file. If None no token is present.
            When a token is supplied, it is looked up with path.
        :param path: The path the request is for, unused unless a token
            is supplied; when supplied it must match the token. The
            value of path is expected to be that from a twisted request.args
            e.g. /foo/bar.
        """
        restricted = self.restricted
        if token and path:
            # With a token and a path we may be able to serve restricted files
            # on the public port.
            #
            # The URL-encoding of the path may have changed somewhere
            # along the line, so reencode it canonically. LFA.filename
            # can't contain slashes, so they're safe to leave unencoded.
            # And urllib.quote erroneously excludes ~ from its safe set,
            # while RFC 3986 says it should be unescaped and Chromium
            # forcibly decodes it in any URL that it sees.
            #
            # This needs to match url_path_quote.
            normalised_path = urllib.quote(urllib.unquote(path), safe='/~+')
            if isinstance(token, Macaroon):
                # Macaroons have enough other constraints that they don't
                # need to be path-specific; it's simpler and faster to just
                # check the alias ID.
                token_ok = threads.blockingCallFromThread(
                    default_reactor, self._verifyMacaroon, token, aliasid)
            else:
                store = session_store()
                token_ok = not store.find(TimeLimitedToken,
                    SQL("age(created) < interval '1 day'"),
                    TimeLimitedToken.token ==
                        hashlib.sha256(token).hexdigest(),
                    TimeLimitedToken.path == normalised_path).is_empty()
                store.reset()
            if token_ok:
                restricted = True
            else:
                raise LookupError("Token stale/pruned/path mismatch")
        alias = LibraryFileAlias.selectOne(And(
            LibraryFileAlias.id == aliasid,
            LibraryFileAlias.contentID == LibraryFileContent.q.id,
            LibraryFileAlias.restricted == restricted))
        if alias is None:
            raise LookupError("No file alias with LibraryFileContent")
        return alias

    def getAliases(self, fileid):
        results = IStore(LibraryFileAlias).find(
            LibraryFileAlias,
            LibraryFileAlias.contentID == LibraryFileContent.id,
            LibraryFileAlias.restricted == self.restricted,
            LibraryFileContent.id == fileid)
        return [(a.id, a.filename, a.mimetype) for a in results]

    # the following methods are used for adding to the library

    def add(self, digest, size, md5_digest, sha256_digest):
        lfc = LibraryFileContent(
            filesize=size, sha1=digest, md5=md5_digest, sha256=sha256_digest)
        return lfc.id

    def addAlias(self, fileid, filename, mimetype, expires=None):
        """Add an alias, and return its ID.

        If a matching alias already exists, it will return that ID instead.
        """
        return LibraryFileAlias(
            contentID=fileid, filename=filename, mimetype=mimetype,
            expires=expires, restricted=self.restricted).id
