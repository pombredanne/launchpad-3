# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""BugTrackerPerson interface."""

__metaclass__ = type
__all__ = [
    'IBugTrackerPerson',
    'IBugTrackerPersonSet',
    ]

from zope.interface import Interface
from zope.schema import Datetime, Object, Text

from canonical.launchpad import _
from canonical.launchpad.interfaces.bugtracker import IBugTracker
from canonical.launchpad.interfaces.launchpad import IHasBug
from canonical.launchpad.interfaces.person import IPerson


class IBugTrackerPerson(IHasBug):
    """A link between a person and a bugtracker."""

    bugtracker = Object(
        schema=IBugTracker, title=u"The bug.", required=True)
    person = Object(
        schema=IPerson, title=_('Person'), required=True)
    name = Text(
        title=_("The name of the person on the bugtracker."),
        required=True)
    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)


class IBugTrackerPersonSet(Interface):
    """A set of IBugTrackerPersons."""

    def getByNameAndBugTracker(name, bugtracker):
        """Return the Person with a given name on a given bugtracker."""

    def linkPersonToBugTracker(person, bugtracker, name):
        """Link a Person to a BugTracker using a given name.

        :param person: The `IPerson` to link to bugtracker.
        :param bugtracker: The `IBugTracker` to which person should be linked.
        :param name: The name used for person on bugtracker.
        :return: An `IBugTrackerPerson`.
        """
