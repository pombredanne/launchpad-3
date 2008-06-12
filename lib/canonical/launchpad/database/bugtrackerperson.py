# Copyright 2008 Canonical Ltd.  All rights reserved.

"""BugTrackerPerson database class."""

__metaclass__ = type
__all__ = [
    'BugTrackerPerson',
    'BugTrackerPersonSet',
    ]

from sqlobject import ForeignKey, StringCol

from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces.bugtrackerperson import (
    IBugTrackerPerson, IBugTrackerPersonSet, BugTrackerNameAlreadyTaken)
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.validators.name import sanitize_name


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

    def ensurePersonForBugTracker(
        self, bugtracker, display_name, email, rationale, creation_comment):
        """Return a Person that is linked to a given bug tracker."""
        # If we have an email address to work with we can use
        # ensurePerson() to get the Person we need.
        if email:
            return getUtility(IPersonSet).ensurePerson(
                email, display_name, rationale, creation_comment)

        # First, see if there's already a BugTrackerPerson for this
        # display_name on this bugtracker. If there is, return it.
        bugtracker_person = self.getByNameAndBugTracker(
            display_name, bugtracker)

        if bugtracker_person is not None:
            return bugtracker_person.person

        # Generate a valid Launchpad name for the Person.
        canonical_name = (
            "%s-%s" % (sanitize_name(display_name), bugtracker.name))
        index = 1

        person_set = getUtility(IPersonSet)
        while person_set.getByName(
            "%s-%d" % (canonical_name, index)) is not None:
            index += 1

        canonical_name = "%s-%d" % (canonical_name, index)
        person = person_set.createPersonWithoutEmail(
            canonical_name, rationale, creation_comment,
            displayname=display_name)

        # Link the Person to the bugtracker for future reference.
        bugtracker_person = self.linkPersonToBugTracker(
            display_name, bugtracker, person)

        return person

    def getByNameAndBugTracker(self, name, bugtracker):
        """Return the Person with a given name on a given bugtracker."""
        return BugTrackerPerson.selectOneBy(name=name, bugtracker=bugtracker)

    def linkPersonToBugTracker(self, name, bugtracker, person):
        """See `IBugTrackerPersonSet`."""
        # Check that this name isn't already in use for the given
        # bugtracker.
        if self.getByNameAndBugTracker(name, bugtracker) is not None:
            raise BugTrackerNameAlreadyTaken(
                "Name '%s' is already in use for bugtracker '%s'." %
                (name, bugtracker.name))

        bugtracker_person = BugTrackerPerson(
            name=name, bugtracker=bugtracker, person=person)

        return bugtracker_person
