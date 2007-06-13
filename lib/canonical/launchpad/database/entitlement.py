# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Entitlement']

from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import EntitlementStatus, IEntitlement

class Entitlement(SQLBase):
    """A table recording the entitlements for a person or team."""

    implements(IEntitlement)

    _table = 'Entitlement'

    # db field names
    person = ForeignKey(dbName='person', foreignKey='Person', default=None, notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_starts = UtcDateTimeCol(notNull=True, default=None)
    date_expires = UtcDateTimeCol(notNull=True, default=None)

    entitlement_type = IntCol(notNull=True)
    quota = IntCol(notNull=True)
    amount_used = IntCol(notNull=True, default=0)
    registrant = ForeignKey(dbName='registrant', foreignKey='Person', default=None, notNull=False)
    approved_by = ForeignKey(dbName='approved_by', foreignKey='Person', default=None, notNull=False)
    status = IntCol(notNull=True, default=0)
    whiteboard = StringCol(notNull=False, default=None)

    @property
    def exceededQuota(self):
        """See IEntitlement."""
        return (self.quota != EntitlementStatus.UNLIMITED and
                self.amount_used > self.quota)
