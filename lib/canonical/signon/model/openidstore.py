# Copyright 2009 Canonical Ltd.  All rights reserved.

"""OpenIDStore implementation for the SSO server's OpenID provider."""

__metaclass__ = type
__all__ = [
    'ProviderOpenIDStore',
    ]

from operator import attrgetter
import time

from openid.association import Association
from openid.store.interface import OpenIDStore
from storm.base import Storm
from storm.properties import Int, RawStr, Unicode
from zope.interface import implements

from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.signon.interfaces.openidstore import IProviderOpenIDStore


class DatabaseAssociation(Storm):
    """Database representation of a stored OpenID association."""

    __storm_table__ = 'OpenIDAssociation'
    __storm_primary__ = ('server_url', 'handle')

    server_url = Unicode()
    handle = Unicode()
    secret = RawStr()
    issued = Int()
    lifetime = Int()
    assoc_type = Unicode()

    def __init__(self, server_url, association):
        super(DatabaseAssociation, self).__init__()
        self.server_url = server_url.decode('UTF-8')
        self.handle = association.handle.decode('ASCII')
        self.secret = association.secret
        self.issued = association.issued
        self.lifetime = association.lifetime
        self.assoc_type = association.assoc_type.decode('ASCII')

    def as_association(self):
        """Return an equivalent openid-python `Association` object."""
        return Association(
            self.handle.encode('ASCII'), self.secret, self.issued,
            self.lifetime, self.assoc_type.encode('ASCII'))


class ProviderOpenIDStore(OpenIDStore):
    """An association store for the OpenID Provider."""
    implements(IProviderOpenIDStore)

    def storeAssociation(self, server_url, association):
        """See `OpenIDStore`."""
        store = IMasterStore(DatabaseAssociation)
        store.add(DatabaseAssociation(server_url, association))

    def getAssociation(self, server_url, handle=None):
        """See `OpenIDStore`."""
        store = IMasterStore(DatabaseAssociation)
        server_url = server_url.decode('UTF-8')
        if handle is None:
            result = store.find(DatabaseAssociation, server_url=server_url)
        else:
            handle = handle.decode('ASCII')
            result = store.find(
                DatabaseAssociation, server_url=server_url, handle=handle)

        db_associations = list(result)
        associations = []
        for db_assoc in db_associations:
            assoc = db_assoc.as_association()
            if assoc.getExpiresIn() == 0:
                store.remove(db_assoc)
            else:
                associations.append(assoc)

        if len(associations) == 0:
            return None
        associations.sort(key=attrgetter('issued'))
        return associations[-1]

    def removeAssociation(self, server_url, handle):
        """See `OpenIDStore`."""
        store = IMasterStore(DatabaseAssociation)
        assoc = store.get(DatabaseAssociation, (
                server_url.decode('UTF-8'), handle.decode('ASCII')))
        if assoc is None:
            return False
        store.remove(assoc)
        return True

    def useNonce(self, server_url, timestamp, salt):
        """See `OpenIDStore`."""
        raise NotImplementedError("OpenID server should not need useNonce")

    def cleanupNonces(self):
        """See `OpenIDStore`."""
        # We don't store nonces, so there are none to clean up.
        return 0

    def cleanupAssociations(self):
        """See `OpenIDStore`."""
        store = IMasterStore(DatabaseAssociation)
        now = int(time.time())
        expired = store.find(
            DatabaseAssociation,
            DatabaseAssociation.issued + DatabaseAssociation.lifetime < now)
        count = expired.count()
        if count > 0:
            expired.remove()
        return count
