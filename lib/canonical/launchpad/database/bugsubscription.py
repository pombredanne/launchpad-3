# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['BugSubscription']

from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces.bugsubscription import IBugSubscription
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.person import validate_public_person


class BugSubscription(SQLBase):
    """A relationship between a person and a bug."""

    implements(IBugSubscription)

    _table = 'BugSubscription'

    person = ForeignKey(dbName='person', foreignKey='Person',
                        notNull=True, storm_validator=validate_public_person)
    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    subscribed_by = ForeignKey(
        dbName='subscribed_by', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)

    @property
    def display_subscribed_by(self):
        """See `IBugSubscription`."""
        if self.person == self.subscribed_by:
            return u'Subscribed themselves'
        else:
            return u'Subscribed by %s' % self.subscribed_by.displayname

    def canBeUnsubscribedByUser(self, user):
        """See `IBugSubscription`."""
        if user.inTeam(getUtility(ILaunchpadCelebrities).admin):
            return True
        if self.person.is_team:
            return user.inTeam(self.person)
        return user == self.person
