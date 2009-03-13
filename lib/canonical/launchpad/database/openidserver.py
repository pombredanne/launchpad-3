# Copyright 2007-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""OpenID related database classes."""

__metaclass__ = type
__all__ = [
    'OpenIDAuthorization',
    'OpenIDAuthorizationSet',
    'OpenIDRPConfig',
    'OpenIDRPConfigSet',
    'OpenIDRPSummary',
    'OpenIDRPSummarySet',
    ]


from datetime import datetime
import pytz
import re

from openid.store.sqlstore import PostgreSQLStore
import psycopg2
from sqlobject import (
    BoolCol, ForeignKey, IntCol, SQLObjectNotFound, StringCol)
from storm.expr import Desc, Or
from storm.store import Store
from zope.component import getUtility
from zope.interface import implements, classProvides

from canonical.database.constants import DEFAULT, UTC_NOW, NEVER_EXPIRES
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import cursor, SQLBase, sqlvalues
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.openidserver import (
    ILaunchpadOpenIDStoreFactory, IOpenIDAuthorization,
    IOpenIDAuthorizationSet, IOpenIDPersistentIdentity, IOpenIDRPConfig,
    IOpenIDRPConfigSet, IOpenIDRPSummary, IOpenIDRPSummarySet)
from canonical.launchpad.interfaces.person import PersonCreationRationale
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE, MASTER_FLAVOR)
from canonical.launchpad.webapp.url import urlparse
from canonical.launchpad.webapp.vhosts import allvhosts


class OpenIDAuthorization(SQLBase):
    implements(IOpenIDAuthorization)

    _table = 'OpenIDAuthorization'

    @staticmethod
    def _get_store():
        """See `SQLBase`.

        The authorization check should always use the master flavor,
        principally because +rp-preauthorize will create them on GET requests.
        """
        return getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    account = ForeignKey(dbName='account', foreignKey='Account', notNull=True)
    client_id = StringCol()
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_expires = UtcDateTimeCol(notNull=True)
    trust_root = StringCol(notNull=True)


class OpenIDAuthorizationSet:
    implements(IOpenIDAuthorizationSet)

    def isAuthorized(self, account, trust_root, client_id):
        """See IOpenIDAuthorizationSet."""
        return  OpenIDAuthorization.select("""
            account = %s
            AND trust_root = %s
            AND date_expires >= CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            AND (client_id IS NULL OR client_id = %s)
            """ % sqlvalues(account, trust_root, client_id)
            ).count() > 0

    def authorize(self, account, trust_root, expires, client_id=None):
        """See IOpenIDAuthorizationSet."""
        if expires is None:
            expires = NEVER_EXPIRES

        existing = OpenIDAuthorization.selectOneBy(
                accountID=account.id,
                trust_root=trust_root,
                client_id=client_id
                )
        if existing is not None:
            existing.date_created = UTC_NOW
            existing.date_expires = expires
        else:
            # Even though OpenIDAuthorizationSet always uses the master
            # store, it's likely that the account can come from the slave.
            # That's why we are using the ID to create the reference.
            OpenIDAuthorization(
                    accountID=account.id, trust_root=trust_root,
                    date_expires=expires, client_id=client_id
                    )

    def getByAccount(self, account):
        """See `IOpenIDAuthorizationSet`."""
        store = Store.of(account)
        result = store.find(OpenIDAuthorization, account=account)
        result.order_by(Desc(OpenIDAuthorization.date_created))
        return result


class OpenIDRPConfig(SQLBase):
    implements(IOpenIDRPConfig)

    _table = 'OpenIDRPConfig'
    trust_root = StringCol(dbName='trust_root', notNull=True)
    displayname = StringCol(dbName='displayname', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    _allowed_sreg = StringCol(dbName='allowed_sreg')
    creation_rationale = EnumCol(
        dbName='creation_rationale', notNull=True,
        schema=PersonCreationRationale,
        default=PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT)
    can_query_any_team = BoolCol(
        dbName='can_query_any_team', notNull=True, default=False)

    def allowed_sreg(self):
        value = self._allowed_sreg
        if not value:
            return []
        return value.split(',')

    def _set_allowed_sreg(self, value):
        if not value:
            self._allowed_sreg = None
        self._allowed_sreg = ','.join(sorted(value))

    allowed_sreg = property(allowed_sreg, _set_allowed_sreg)


class OpenIDRPConfigSet:
    implements(IOpenIDRPConfigSet)

    url_re = re.compile("^(.+?)\/*$")

    def _normalizeTrustRoot(self, trust_root):
        """Given a trust root URL ensure it ends with exactly one '/'."""
        match = self.url_re.match(trust_root)
        assert match is not None, (
            "Attempting to normalize trust root %s failed." % trust_root)
        return "%s/" % match.group(1)

    def new(self, trust_root, displayname, description, logo=None,
            allowed_sreg=None,
            creation_rationale=
                PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT,
            can_query_any_team=False):
        """See `IOpenIDRPConfigSet`"""
        if allowed_sreg:
            allowed_sreg = ','.join(sorted(allowed_sreg))
        else:
            allowed_sreg = None
        trust_root = self._normalizeTrustRoot(trust_root)
        return OpenIDRPConfig(
            trust_root=trust_root, displayname=displayname,
            description=description, logo=logo,
            _allowed_sreg=allowed_sreg, creation_rationale=creation_rationale,
            can_query_any_team=can_query_any_team)

    def get(self, id):
        """See `IOpenIDRPConfigSet`"""
        try:
            return OpenIDRPConfig.get(id)
        except SQLObjectNotFound:
            return None

    def getAll(self):
        """See `IOpenIDRPConfigSet`"""
        return OpenIDRPConfig.select(orderBy=['displayname', 'trust_root'])

    def getByTrustRoot(self, trust_root):
        """See `IOpenIDRPConfigSet`"""
        trust_root = self._normalizeTrustRoot(trust_root)
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        # XXX: BradCrittenden 2008-09-26 bug=274774: Until the database is
        # updated to normalize existing data the query must look for
        # trust_roots that end in '/' and those that do not.
        return store.find(
            OpenIDRPConfig,
            Or(OpenIDRPConfig.trust_root==trust_root,
               OpenIDRPConfig.trust_root==trust_root[:-1])).one()


class LaunchpadOpenIDStore(PostgreSQLStore):
    """The standard OpenID Library PostgreSQL store with overrides to
    ensure it plays nicely with Zope3 and Launchpad.

    It is registered as a factory to provide a way for instances to be
    created from browser code without warnings, as getUtility is not
    suitable as this class is not thread safe.
    """
    classProvides(ILaunchpadOpenIDStoreFactory)

    exceptions = psycopg2
    settings_table = None
    associations_table = 'OpenIDAssociations'
    nonces_table = None

    def __init__(self):
        # No need to pass in the connection - we have better ways of
        # getting a cursor.
        PostgreSQLStore.__init__(self, None)

    def _callInTransaction(self, func, *args, **kwargs):
        """Open a fresh cursor and call the given method.

        No transactional semantics in Launchpad because Z3 is already
        fully transactional so there is no need to reinvent the wheel.
        """
        self.cur = cursor()
        try:
            return func(*args, **kwargs)
        finally:
            self.cur.close()
            self.cur = None

    def createTables(self):
        """Not desired in Launchpad - raise an exception."""
        raise AssertionError("Tables should not be created automatically")

    txn_createTables = createTables


class OpenIDRPSummary(SQLBase):
    """A summary of the interaction between a `IAccount` and an OpenID RP."""
    implements(IOpenIDRPSummary)
    _table = 'OpenIDRPSummary'

    account = ForeignKey(dbName='account', foreignKey='Account', notNull=True)
    openid_identifier = StringCol(notNull=True)
    trust_root = StringCol(notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_last_used = UtcDateTimeCol(notNull=True, default=DEFAULT)
    total_logins = IntCol(notNull=True, default=1)

    def increment(self, date_used=None):
        """See `IOpenIDRPSummary`.

        :param date_used: an optional datetime the login happened. The current
            datetime is used if date_used is None.
        """
        self.total_logins = self.total_logins + 1
        if date_used is None:
            date_used = datetime.now(pytz.UTC)
        self.date_last_used = date_used


class OpenIDRPSummarySet:
    """A set of OpenID RP Summaries."""
    implements(IOpenIDRPSummarySet)

    def getByIdentifier(self, identifier, only_unknown_trust_roots=False):
        """See `IOpenIDRPSummarySet`."""
        # XXX: flacoste 2008-11-17 bug=274774: Normalize the trust_root
        # in OpenIDRPSummary.
        if only_unknown_trust_roots:
            result = OpenIDRPSummary.select("""
            CASE
                WHEN OpenIDRPSummary.trust_root LIKE '%%/'
                THEN OpenIDRPSummary.trust_root
                ELSE OpenIDRPSummary.trust_root || '/'
            END NOT IN (SELECT trust_root FROM OpenIdRPConfig)
            AND openid_identifier = %s
                """ % sqlvalues(identifier))
        else:
            result = OpenIDRPSummary.selectBy(openid_identifier=identifier)
        return result.orderBy('id')

    def _assert_identifier_is_not_reused(self, account, identifier):
        """Assert no other account in the summaries has the identifier."""
        summaries = OpenIDRPSummary.select("""
            account != %s
            AND openid_identifier = %s
            """ % sqlvalues(account, identifier))
        if summaries.count() > 0:
            raise AssertionError(
                'More than 1 account has the OpenID identifier of %s.' %
                identifier)

    def record(self, account, trust_root, date_used=None):
        """See `IOpenIDRPSummarySet`.

        :param date_used: an optional datetime the login happened. The current
            datetime is used if date_used is None.
        :raise AssertionError: If the account is not ACTIVE.
        :return: An `IOpenIDRPSummary` or None if the trust_root is
            Launchpad or one of its vhosts.
        """
        trust_site = urlparse(trust_root)[1]
        launchpad_site = allvhosts.configs['mainsite'].hostname
        if trust_site.endswith(launchpad_site):
            return None
        if account.status != AccountStatus.ACTIVE:
            raise AssertionError(
                'Account %d is not ACTIVE account.' % account.id)
        identifier = IOpenIDPersistentIdentity(account).openid_identity_url
        self._assert_identifier_is_not_reused(account, identifier)
        if date_used is None:
            date_used = datetime.now(pytz.UTC)
        summary = OpenIDRPSummary.selectOneBy(
            account=account, openid_identifier=identifier,
            trust_root=trust_root)
        if summary is not None:
            # Update the existing summary.
            summary.increment(date_used=date_used)
        else:
            # create a new summary.
            summary = OpenIDRPSummary(
                account=account, openid_identifier=identifier,
                trust_root=trust_root, date_created=date_used,
                date_last_used=date_used, total_logins=1)
        return summary
