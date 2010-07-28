# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscription']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase

from lp.bugs.interfaces.bugsubscription import IBugSubscription


class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table = 'BugSubscription'

    person = ForeignKey(
        dbName='person', foreignKey='Person',
        notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    subscribed_by = ForeignKey(
        dbName='subscribed_by', foreignKey='Person',
        notNull=True)

    @property
    def display_subscribed_by(self):
        """See `IBugSubscription`."""
        if self.person == self.subscribed_by:
            return u'Subscribed themselves'
        else:
            return u'Subscribed by %s' % self.subscribed_by.displayname

    def canBeUnsubscribedByUser(self, user):
        """See `IBugSubscription`."""
        if user is None:
            return False
        if self.person.is_team:
            return user.inTeam(self.person)
        return user == self.person
