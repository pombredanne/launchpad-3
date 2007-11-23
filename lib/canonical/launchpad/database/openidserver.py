# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""OpenID related database classes."""

__metaclass__ = type
__all__ = [
    'OpenIdAuthorization', 'OpenIdAuthorizationSet', 'OpenIDRPConfig',
    'OpenIDRPConfigSet']

from random import random
from time import time

from zope.interface import implements, classProvides

from sqlobject import ForeignKey, SQLObjectNotFound, StringCol

from openid.store.sqlstore import PostgreSQLStore

from canonical.database.constants import DEFAULT, UTC_NOW, NEVER_EXPIRES
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import cursor, SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
    IOpenIdAuthorization, IOpenIdAuthorizationSet, IOpenIDRPConfig,
    IOpenIDRPConfigSet, ILaunchpadOpenIdStoreFactory,
    PersonCreationRationale)

class OpenIdAuthorization(SQLBase):
    implements(IOpenIdAuthorization)
    _table = 'OpenIdAuthorization'
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)
    client_id = StringCol()
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_expires = UtcDateTimeCol(notNull=True)
    trust_root = StringCol(notNull=True)


class OpenIdAuthorizationSet:
    implements(IOpenIdAuthorizationSet)

    def isAuthorized(self, person, trust_root, client_id):
        """See IOpenIdAuthorizationSet."""
        return  OpenIdAuthorization.select("""
            person = %s
            AND trust_root = %s
            AND date_expires >= CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            AND (client_id IS NULL OR client_id = %s)
            """ % sqlvalues(person.id, trust_root, client_id)).count() > 0

    def authorize(self, person, trust_root, expires, client_id=None):
        """See IOpenIdAuthorizationSet."""
        if expires is None:
            expires = NEVER_EXPIRES

        assert not person.isTeam(), 'Attempting to authorize a team.'

        existing = OpenIdAuthorization.selectOneBy(
                personID=person.id,
                trust_root=trust_root,
                client_id=client_id
                )
        if existing is not None:
            existing.date_created = UTC_NOW
            existing.date_expires = expires
        else:
            OpenIdAuthorization(
                    person=person, trust_root=trust_root,
                    date_expires=expires, client_id=client_id
                    )


class OpenIDRPConfig(SQLBase):
    implements(IOpenIDRPConfig)

    _table = 'OpenIdRPConfig'
    trust_root = StringCol(dbName='trust_root', notNull=True)
    displayname = StringCol(dbName='displayname', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    logo = ForeignKey(
        dbName='logo', foreignKey='LibraryFileAlias', default=None)
    _allowed_sreg = StringCol(dbName='allowed_sreg', forceDBName=True)
    creation_rationale = EnumCol(
        dbName='creation_rationale', notNull=True,
        schema=PersonCreationRationale,
        default=PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT)

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

    def new(self, trust_root, displayname, description, logo=None,
            allowed_sreg=None,
            creation_rationale=PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT):
        """See `IOpenIdRPConfigSet`"""
        if allowed_sreg:
            allowed_sreg = ','.join(sorted(allowed_sreg))
        else:
            allowed_sreg = None
        return OpenIDRPConfig(
            trust_root=trust_root, displayname=displayname,
            description=description, logo=logo,
            _allowed_sreg=allowed_sreg, creation_rationale=creation_rationale)

    def get(self, id):
        """See `IOpenIdRPConfigSet`"""
        try:
            return OpenIDRPConfig.get(id)
        except SQLObjectNotFound:
            return None

    def getAll(self):
        """See `IOpenIdRPConfigSet`"""
        return OpenIDRPConfig.select()

    def getByTrustRoot(self, trust_root):
        """See `IOpenIdRPConfigSet`"""
        return OpenIDRPConfig.selectOneBy(trust_root=trust_root)


class LaunchpadOpenIdStore(PostgreSQLStore):
    """The standard OpenID Library PostgreSQL store with overrides to
    ensure it plays nicely with Zope3 and Launchpad.

    It is registered as a factory to provide a way for instances to be
    created from browser code without warnings, as getUtility is not
    suitable as this class is not thread safe.
    """
    classProvides(ILaunchpadOpenIdStoreFactory)

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

