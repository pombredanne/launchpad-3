# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Interfaces for a Sprint (a meeting, conference or hack session). A Sprint
basically consists of a bunch of people getting together to discuss some
specific issues.
"""

__metaclass__ = type

__all__ = [
    'ISprint',
    'ISprintSet',
    ]

from zope.i18nmessageid import MessageIDFactory

from zope.interface import Interface, Attribute

from zope.schema import Datetime, Int, Choice, Text, TextLine

from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces import IHasOwner


_ = MessageIDFactory('launchpad')


class ISprint(IHasOwner):
    """A sprint, or conference, or meeting."""

    name = TextLine(
        title=_('Name'), required=True, description=_('A unique name '
        'for this sprint, or conference, or meeting. This will part of '
        'the URL so pick something short. A single word is all you get.'),
        constraint=valid_name)
    title = TextLine(
        title=_('Title'), required=True, description=_("Please provide "
        "a title for this meeting. This will be shown in listings of "
        "meetings."))
    summary = Text(
        title=_('Summary'), required=True, description=_("A one-paragraph "
        "summary of the meeting plans and goals. Put the rest in a web "
        "page and link to it using the field below."))
    address = Text(
        title=_('Meeting Address'), required=False,
        description=_("The address of the meeting venue."))
    home_page = TextLine(
        title=_('Home Page'), required=False, description=_("A web page "
        "with further information about the event."))
    owner = Choice(title=_('Owner'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    time_zone = Choice(
        title=_('Timezone'), required=True, description=_('The time '
        'zone in which this sprint, or conference, takes place. '),
        vocabulary='TimezoneName')
    time_starts = Datetime(
        title=_('Starting Date and Time'), required=True)
    time_ends = Datetime(
        title=_('Finishing Date and Time'), required=True)
    datecreated = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    # joins
    attendees = Attribute('The set of attendees at this sprint.')
    attendances = Attribute('The set of SprintAttendance records.')
    specifications = Attribute("Specifications to be discussed at this "
        "sprint.")
    
    def specificationLinks(status=None):
        """Return the SprintSpecification records matching the status given,
        or all of them if no status is passed.
        """

    # subscription-related methods
    def attend(person, time_starts, time_ends):
        """Record that this person will be attending the Sprint."""
        
    def removeAttendance(person):
        """Remove the person's attendance record."""

    # bug linking
    def linkSpecification(spec):
        """Link this sprint to the given specification."""

    def unlinkSpecification(spec):
        """Remove this specification from the sprint spec list."""


# Interfaces for containers
class ISprintSet(Interface):
    """A container for sprints."""

    title = Attribute('Title')

    def __iter__():
        """Iterate over all Sprints, in reverse time_start order."""

    def __getitem__(name):
        """Get a specific Sprint."""

    def new(owner, name, title, time_starts, time_ends, summary=None,
        description=None):
        """Create a new sprint."""


