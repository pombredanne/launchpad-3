# Copyright 2007-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""OpenID related database classes."""

__metaclass__ = type
__all__ = [
    'OpenIDAuthorization',
    'OpenIDAuthorizationSet',
    'OpenIDRPSummary',
    'OpenIDRPSummarySet',
    ]


from sqlobject import ForeignKey, StringCol
from storm.expr import Desc, Or
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import DEFAULT, UTC_NOW, NEVER_EXPIRES
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IMasterStore, IStore
from canonical.launchpad.webapp.interfaces import (
    AUTH_STORE, IStoreSelector, MASTER_FLAVOR)
from canonical.signon.interfaces.openidserver import (
    IOpenIDAuthorization, IOpenIDAuthorizationSet)


class OpenIDAuthorization(SQLBase):
    implements(IOpenIDAuthorization)

    _table = 'OpenIDAuthorization'

    @staticmethod
    def _get_store():
        """See `SQLBase`.

        The authorization check should always use the master flavor,
        principally because +rp-preauthorize will create them on GET requests.
        """
        return getUtility(IStoreSelector).get(AUTH_STORE, MASTER_FLAVOR)

    account = ForeignKey(dbName='account', foreignKey='Account', notNull=True)
    client_id = StringCol()
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_expires = UtcDateTimeCol(notNull=True)
    trust_root = StringCol(notNull=True)


class OpenIDAuthorizationSet:
    implements(IOpenIDAuthorizationSet)

    def isAuthorized(self, account, trust_root, client_id):
        """See IOpenIDAuthorizationSet.
        
        The use of the master Store is forced to avoid replication
        race conditions.
        """
        return IMasterStore(OpenIDAuthorization).find(
            OpenIDAuthorization,
            # Use account.id here just incase it is from a different Store.
            OpenIDAuthorization.accountID == account.id,
            OpenIDAuthorization.trust_root == trust_root,
            OpenIDAuthorization.date_expires >= UTC_NOW,
            Or(
                OpenIDAuthorization.client_id == None,
                OpenIDAuthorization.client_id == client_id)).count() > 0

    def authorize(self, account, trust_root, expires, client_id=None):
        """See IOpenIDAuthorizationSet."""
        if expires is None:
            expires = NEVER_EXPIRES

        # It's likely that the account can come from the slave.
        # That's why we are using the ID to create the reference.
        existing = IMasterStore(OpenIDAuthorization).find(
            OpenIDAuthorization,
            accountID=account.id,
            trust_root=trust_root,
            client_id=client_id).one()

        if existing is not None:
            existing.date_created = UTC_NOW
            existing.date_expires = expires
        else:
            OpenIDAuthorization(
                accountID=account.id, trust_root=trust_root,
                date_expires=expires, client_id=client_id
                )

    def getByAccount(self, account):
        """See `IOpenIDAuthorizationSet`."""
        store = IStore(OpenIDAuthorization)
        result = store.find(OpenIDAuthorization, accountID=account.id)
        result.order_by(Desc(OpenIDAuthorization.date_created))
        return result
