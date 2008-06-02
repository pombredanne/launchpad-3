# Copyright 2008 Canonical Ltd.  All rights reserved.

"""BugTrackerPerson database class."""

__metaclass__ = type
__all__ = [
    'BugTrackerPerson',
    'BugTrackerPersonSet',
    ]

from sqlobject import ForeignKey, StringCol
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces.bugtrackerperson import (
    IBugTrackerPerson, IBugTrackerPersonSet)


class BugTrackerPerson(SQLBase):
    """See `IBugTrackerPerson`."""

    implements(IBugTrackerPerson)

    bugtracker = ForeignKey(
        dbName='bugtracker', foreignKey='BugTracker', notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person', notNull=True)
    name = StringCol(notNull=True)
    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)


class BugTrackerPersonSet:
    """See `IMessageSet`."""

    implements(IBugTrackerPersonSet)

    def getByNameAndBugTracker(self, name, bugtracker):
        """Return the Person with a given name on a given bugtracker."""
        return BugTrackerPerson.selectOneBy(name=name, bugtracker=bugtracker)

    def linkPersonToBugTracker(self, person, bugtracker, name):
        """See `IBugTrackerPersonSet`."""
        bugtracker_person = BugTrackerPerson(
            bugtracker=bugtracker, name=name, person=person)

        return bugtracker_person
