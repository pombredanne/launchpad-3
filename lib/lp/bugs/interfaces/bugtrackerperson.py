# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""BugTrackerPerson interface."""

__metaclass__ = type
__all__ = [
    'IBugTrackerPerson',
    'BugTrackerPersonAlreadyExists',
    ]

from zope.schema import (
    Datetime,
    Object,
    Text,
    )

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import IHasBug
from lp.bugs.interfaces.bugtracker import IBugTracker
from lp.registry.interfaces.person import IPerson


class BugTrackerPersonAlreadyExists(Exception):
    """An `IBugTrackerPerson` with the given name already exists."""


class IBugTrackerPerson(IHasBug):
    """A link between a person and a bugtracker."""

    bugtracker = Object(
        schema=IBugTracker, title=_('The bug.'), required=True)
    person = Object(
        schema=IPerson, title=_('Person'), required=True)
    name = Text(
        title=_("The name of the person on the bugtracker."),
        required=True)
    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)
