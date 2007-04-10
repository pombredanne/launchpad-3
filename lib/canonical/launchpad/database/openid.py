# Copyright 2007 Canonical Ltd.  All rights reserved.

"""OpenID related database classes."""

__metaclass__ = type
__all__ = ['OpenIdAuthorization', 'OpenIdAuthorizationSet']

from zope.interface import implements

from sqlobject import StringCol, ForeignKey

from canonical.database.constants import DEFAULT, UTC_NOW, NEVER_EXPIRES
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import cursor, SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
        IOpenIdAuthorization, IOpenIdAuthorizationSet,
        )

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
        cur = cursor()
        cur.execute("""
            SELECT TRUE FROM OpenIdAuthorization
            WHERE person = %s
                AND trust_root = %s
                AND date_expires >= CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                AND (client_id IS NULL OR client_id = %s)
            LIMIT 1
            """ % sqlvalues(person.id, trust_root, client_id))
        if cur.fetchone() is None:
            return False
        else:
            return True

    def authorize(self, person, trust_root, expires, client_id=None):
        """Authorize the trust_root for the given person.

        If expires is None, the authorization never expires.
        
        If client_id is None, authorization is given to any client.
        If client_id is not None, authorization is only given to the client
        with the specified client_id (ie. the session cookie token).

        This method overrides any existing authorization for the given
        (person, trust_root, client_id).
        """
        if expires is None:
            expires = NEVER_EXPIRES

        existing = OpenIdAuthorization.selectOneBy(
                personID=person.id,
                trust_root=trust_root,
                client_id=client_id
                )
        if existing is not None:
            existing.date_created = UTC_NOW
            existing.expires = expires
        else:
            OpenIdAuthorization(
                    person=person, trust_root=trust_root,
                    expires=expires, client_id=client_id
                    )

