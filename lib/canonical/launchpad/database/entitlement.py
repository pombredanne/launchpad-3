# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Entitlement']

from datetime import datetime
import pytz

from zope.interface import implements

from sqlobject import ForeignKey, IntCol, StringCol

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    EntitlementInvalidError, EntitlementQuota, EntitlementQuotaExceededError,
    IEntitlement)

from canonical.lp.dbschema import EntitlementState, EntitlementType

class Entitlement(SQLBase):
    """A table recording the entitlements for a person or team."""

    implements(IEntitlement)

    _table = 'Entitlement'

    person = ForeignKey(
        dbName='person', foreignKey='Person',
        default=None, notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_starts = UtcDateTimeCol(notNull=False, default=None)
    date_expires = UtcDateTimeCol(notNull=False, default=None)

    entitlement_type = EnumCol(
        dbName='entitlement_type',
        notNull=True,
        schema=EntitlementType,
        default=EntitlementType.PRIVATE_BUGS)
    quota = IntCol(notNull=True)
    amount_used = IntCol(notNull=True, default=0)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        default=None, notNull=False)
    approved_by = ForeignKey(
        dbName='approved_by', foreignKey='Person',
        default=None, notNull=False)
    state = EnumCol(
        dbName='state',
        notNull=True,
        schema=EntitlementState,
        default=EntitlementState.INACTIVE)
    whiteboard = StringCol(notNull=False, default=None)

    @property
    def exceeded_quota(self):
        """See IEntitlement."""
        if self.quota == EntitlementQuota.UNLIMITED:
            return False
        else:
            return self.amount_used > self.quota

    def _isExpired(self, now=None):
        if now is None:
            now = datetime.now(pytz.timezone('UTC'))
        if self.date_expires is None:
            return False
        else:
            return now > self.date_expires

    def _hasNotYetStarted(self, now=None):
        if now is None:
            now = datetime.now(pytz.timezone('UTC'))
        if self.date_starts is None:
            return False
        else:
            return now < self.date_starts

    @property
    def in_date_range(self):
        """See IEntitlement."""
        now = datetime.now(pytz.timezone('UTC'))
        too_late = self._isExpired(now)
        too_early = self._hasNotYetStarted(now)
        just_right = not (too_late or too_early)
        return just_right

    @property
    def is_valid(self):
        """See IEntitlement."""
        if self.state != EntitlementState.ACTIVE:
            return False
        else:
            return self.in_date_range and not self.exceeded_quota

    def incrementAmountUsed(self):
        """See IEntitlement."""
        if not self.is_valid:
            raise EntitlementInvalidError(
                "This entitlement is invalid and cannot be used.")

        self.amount_used += 1

        if self.exceeded_quota:
            self.amount_used -= 1
            raise EntitlementQuotaExceededError(
                "The quota for this entitlement has been exceeded.")
