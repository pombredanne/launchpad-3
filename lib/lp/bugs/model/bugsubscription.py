# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscription']

from sqlobject import ForeignKey
from storm.base import Storm
from storm.locals import (
    Bool,
    Int,
    Reference,
    Unicode,
    )
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import (
    DBEnum,
    EnumCol,
    )
from canonical.database.sqlbase import SQLBase
from lp.bugs.interfaces.bugsubscription import IBugSubscription
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.person import validate_person


class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table = 'BugSubscription'

    person = ForeignKey(
        dbName='person', foreignKey='Person',
        storm_validator=validate_person,
        notNull=True
        )
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    bug_notification_level = EnumCol(
        enum=BugNotificationLevel,
        default=BugNotificationLevel.COMMENTS,
        notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    subscribed_by = ForeignKey(
        dbName='subscribed_by', foreignKey='Person',
        storm_validator=validate_person,
        notNull=True
        )

    @property
    def display_subscribed_by(self):
        """See `IBugSubscription`."""
        if self.person == self.subscribed_by:
            return u'Self-subscribed'
        else:
            return u'Subscribed by %s' % self.subscribed_by.displayname

    @property
    def display_duplicate_subscribed_by(self):
        """See `IBugSubscription`."""
        if self.person == self.subscribed_by:
            return u'Self-subscribed to bug %s' % (self.bugID)
        else:
            return u'Subscribed to bug %s by %s' % (self.bugID,
                self.subscribed_by.displayname)

    def canBeUnsubscribedByUser(self, user):
        """See `IBugSubscription`."""
        if user is None:
            return False
        if self.person.is_team:
            return user.inTeam(self.person)
        return user == self.person


class BugSubscriptionFilter(Storm):

    __storm_table__ = "BugSubscriptionFilter"

    id = Int(primary=True)

    structural_subscription_id = Int("structuralsubscription", allow_none=False)
    structural_subscription = Reference(
        structural_subscription_id, "StructuralSubscription.id")

    find_all_tags = Bool(allow_none=False, default=False)
    include_any_tags = Bool(allow_none=False, default=False)
    exclude_any_tags = Bool(allow_none=False, default=False)

    other_parameters = Unicode()

    description = Unicode()


class BugSubscriptionFilterStatus(Storm):

    __storm_table__ = "BugSubscriptionFilterStatus"

    id = Int(primary=True)

    filter_id = Int("filter", allow_none=False)
    filter = Reference(filter_id, "BugSubscriptionFilter.id")

    status = DBEnum(enum=BugTaskStatus, allow_none=False)


class BugSubscriptionFilterImportance(Storm):

    __storm_table__ = "BugSubscriptionFilterImportance"

    id = Int(primary=True)

    filter_id = Int("filter", allow_none=False)
    filter = Reference(filter_id, "BugSubscriptionFilter.id")

    importance = DBEnum(enum=BugTaskImportance, allow_none=False)


class BugSubscriptionFilterTag(Storm):

    __storm_table__ = "BugSubscriptionFilterTag"

    id = Int(primary=True)

    filter_id = Int("filter", allow_none=False)
    filter = Reference(filter_id, "BugSubscriptionFilter.id")

    include = Bool(allow_none=False)
    tag = Unicode(allow_none=False)
