# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscription']

import pytz
from storm.locals import (
    DateTime,
    Int,
    Reference,
    )
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum
from lp.bugs.interfaces.bugsubscription import IBugSubscription
from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.person import validate_person
from lp.services.stormbase import StormBase


class BugSubscription(StormBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    __storm_table__ = 'BugSubscription'

    id = Int(primary=True)

    person_id = Int(
        "person", allow_none=False, validator=validate_person)
    person = Reference(person_id, "Person.id")

    bug_id = Int("bug", allow_none=False)
    bug = Reference(bug_id, "Bug.id")

    bug_notification_level = DBEnum(
        enum=BugNotificationLevel,
        default=BugNotificationLevel.COMMENTS,
        allow_none=False)

    date_created = DateTime(
        allow_none=False, default=UTC_NOW, tzinfo=pytz.UTC)

    subscribed_by_id = Int(
        "subscribed_by", allow_none=False, validator=validate_person)
    subscribed_by = Reference(subscribed_by_id, "Person.id")

    def __init__(self, bug=None, person=None, subscribed_by=None,
                 bug_notification_level=BugNotificationLevel.COMMENTS):
        super(BugSubscription, self).__init__()
        self.bug = bug
        self.person = person
        self.subscribed_by = subscribed_by
        self.bug_notification_level = bug_notification_level

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
            return u'Self-subscribed to bug %s' % (self.bug_id)
        else:
            return u'Subscribed to bug %s by %s' % (self.bug_id,
                self.subscribed_by.displayname)

    def canBeUnsubscribedByUser(self, user):
        """See `IBugSubscription`."""
        if user is None:
            return False
        if self.person.is_team:
            return user.inTeam(self.person)
        return user == self.person
