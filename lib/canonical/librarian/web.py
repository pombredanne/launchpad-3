# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
#

__metaclass__ = type

from datetime import datetime

from twisted.web import resource, static, error, util, server, proxy
from twisted.internet.threads import deferToThread
from pytz import utc

from canonical.librarian.client import quote
from canonical.librarian.db import read_transaction, write_transaction
from canonical.librarian.utils import guess_librarian_encoding


defaultResource = static.Data("""
        <html>
        <body>
        <h1>Launchpad Librarian</h1>
        <p>
        http://librarian.launchpad.net/ is a
        file repository used by <a href="https://launchpad.net/">Launchpad</a>.
        </p>
        <p><small>Copyright 2004-2007 Canonical Ltd.</small></p>
        <!-- kthxbye. -->
        </body></html>
        """, type='text/html')
fourOhFour = error.NoResource('No such resource')


class NotFound(Exception):
    pass


class LibraryFileResource(resource.Resource):
    def __init__(self, storage, upstreamHost, upstreamPort):
        resource.Resource.__init__(self)
        self.storage = storage
        self.upstreamHost = upstreamHost
        self.upstreamPort = upstreamPort

    def getChild(self, name, request):
        if name == '':
            # Root resource
            return defaultResource
        try:
            aliasID = int(name)
        except ValueError:
            return fourOhFour

        return LibraryFileAliasResource(self.storage, aliasID,
                self.upstreamHost, self.upstreamPort)


class LibraryFileAliasResource(resource.Resource):
    def __init__(self, storage, aliasID, upstreamHost, upstreamPort):
        resource.Resource.__init__(self)
        self.storage = storage
        self.aliasID = aliasID
        self.upstreamHost = upstreamHost
        self.upstreamPort = upstreamPort

    def getChild(self, filename, request):

        # If we still have another component of the path, then we have
        # an old URL that encodes the content ID. We want to keep supporting
        # these, so we just ignore the content id that is currently in
        # self.aliasID and extract the real one from the URL.
        if len(request.postpath) == 1:
            try:
                self.aliasID = int(filename)
            except ValueError:
                return fourOhFour
            filename = request.postpath[0]

        deferred = deferToThread(self._getFileAlias, self.aliasID)
        deferred.addCallback(
                self._cb_getFileAlias, filename, request
                )
        deferred.addErrback(self._eb_getFileAlias)
        return util.DeferredResource(deferred)

    @write_transaction
    def _getFileAlias(self, aliasID):
        try:
            alias = self.storage.getFileAlias(aliasID)
            alias.updateLastAccessed()
            return (alias.contentID, alias.filename,
                alias.mimetype, alias.date_created)
        except LookupError:
            raise NotFound

    def _eb_getFileAlias(self, failure):
        failure.trap(NotFound)
        return fourOhFour

    def _cb_getFileAlias(
            self, (dbcontentID, dbfilename, mimetype, date_created),
            filename, request
            ):
        # Return a 404 if the filename in the URL is incorrect. This offers
        # a crude form of access control (stuff we care about can have
        # unguessable names effectively using the filename as a secret).
        if dbfilename.encode('utf-8') != filename:
            return fourOhFour

        # Set our caching headers, dynamically based on the creation date,
        # per Bug 5456.
        now = datetime.utcnow().replace(tzinfo=utc)
        age = now - date_created
        age_seconds = max(age.days * 24 * 60 + age.seconds, 2 * 24 * 60)
        request.setHeader('Cache-Control', 'max-age=%d, public' % age_seconds)
        #request.setHeader('Last-Modified',
        #    date_created.strftime('%a, %d %b %Y %H:%M:%S +0000'))
        request.lastModified = date_created.toordinal()

        if self.storage.hasFile(dbcontentID) or self.upstreamHost is None:
            # XXX: Brad Crittenden 2007-12-05 bug=174204: When encodings are
            # stored as part of a file's metadata this logic will be replaced.
            encoding, mimetype = guess_librarian_encoding(filename, mimetype)
            return File(mimetype, encoding,
                        self.storage._fileLocation(dbcontentID))
        else:
            return proxy.ReverseProxyResource(self.upstreamHost,
                                              self.upstreamPort, request.path)

    def render_GET(self, request):
        return defaultResource.render(request)


class File(static.File):
    isLeaf = True
    def __init__(self, contentType, encoding=None, *args, **kwargs):
        static.File.__init__(self, *args, **kwargs)
        self.type = contentType
        self.encoding = encoding


class DigestSearchResource(resource.Resource):
    def __init__(self, storage):
        self.storage = storage
        resource.Resource.__init__(self)

    def render_GET(self, request):
        try:
            digest = request.args['digest'][0]
        except LookupError:
            return static.Data('Bad search', 'text/plain').render(request)

        deferred = deferToThread(self._matchingAliases, digest)
        deferred.addCallback(self._cb_matchingAliases, request)
        deferred.addErrback(_eb, request)
        return server.NOT_DONE_YET

    @read_transaction
    def _matchingAliases(self, digest):
        library = self.storage.library
        matches = ['%s/%s' % (aID, quote(aName))
                   for fID in library.lookupBySHA1(digest)
                   for aID, aName, aType in library.getAliases(fID)]
        return matches

    def _cb_matchingAliases(self, matches, request):
        text = '\n'.join([str(len(matches))] + matches)
        response = static.Data(text.encode('utf-8'),
                               'text/plain; charset=utf-8').render(request)
        request.write(response)
        request.finish()


# Ask robots not to index or archive anything in the librarian.
robotsTxt = static.Data("""
User-agent: *
Disallow: /
""", type='text/plain')


def _eb(failure, request):
    """Generic errback for failures during a render_GET."""
    request.processingFailed(failure)
