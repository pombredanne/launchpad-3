# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['Entitlement', 'EntitlementSet']

from datetime import datetime

import pytz
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLObjectNotFound,
    StringCol,
    )
from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from lp.app.errors import NotFoundError
from lp.registry.interfaces.entitlement import (
    EntitlementInvalidError,
    EntitlementQuota,
    EntitlementQuotaExceededError,
    EntitlementState,
    EntitlementType,
    IEntitlement,
    IEntitlementSet,
    )


class Entitlement(SQLBase):
    """A table recording the entitlements for a person or team."""

    implements(IEntitlement)
    _table = 'Entitlement'
    _defaultOrder = ['person', '-date_expires']

    person = ForeignKey(
        dbName='person', foreignKey='Person',
        default=None, notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    date_starts = UtcDateTimeCol(notNull=False, default=None)
    date_expires = UtcDateTimeCol(notNull=False, default=None)

    entitlement_type = EnumCol(
        dbName='entitlement_type',
        notNull=True,
        enum=EntitlementType,
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
        enum=EntitlementState,
        default=EntitlementState.INACTIVE)
    whiteboard = StringCol(notNull=False, default=None)
    is_dirty = BoolCol(dbName="is_dirty", notNull=True, default=True)

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


class EntitlementSet:
    """The set of all entitlements."""

    implements(IEntitlementSet)

    def __getitem__(self, entitlement_id):
        """See `IEntitlementSet`."""
        entitlement = self.get(entitlement_id)
        if entitlement is None:
            raise NotFoundError(entitlement_id)
        return entitlement

    def __iter__(self):
        """See `IEntitlementSet`."""
        return iter(Entitlement.select())

    def count(self):
        """See `IEntitlementSet`."""
        return Entitlement.select().count()

    def get(self, entitlement_id, default=None):
        """See `IEntitlementSet`."""
        try:
            return Entitlement.get(entitlement_id)
        except SQLObjectNotFound:
            return default

    def getForPerson(self, person):
        """See `IEntitlementSet`."""
        return Entitlement.selectBy(person=person)

    def getValidForPerson(self, person):
        """See `IEntitlementSet`."""
        entitlements = self.getForPerson(person)
        return [entitlement for entitlement in entitlements
                if entitlement.is_valid]

    def getDirty(self):
        """See `IEntitlementSet`."""
        return Entitlement.selectBy(is_dirty=True)

    def new(self, person, quota, entitlement_type,
            state, is_dirty=True, date_created=None, date_starts=None,
            date_expires=None, amount_used=0, registrant=None,
            approved_by=None, whiteboard=None):
        """See `IEntitlementSet`."""

        if date_created is None:
            date_created = datetime.now(pytz.timezone('UTC'))

        return Entitlement(
            person=person,
            quota=quota,
            entitlement_type=entitlement_type,
            state=state,
            is_dirty=is_dirty,
            date_created=date_created,
            date_starts=date_starts,
            date_expires=date_expires,
            amount_used=amount_used,
            registrant=registrant,
            approved_by=approved_by,
            whiteboard=whiteboard)
