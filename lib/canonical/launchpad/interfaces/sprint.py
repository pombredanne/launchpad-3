# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Interfaces for a Sprint (a meeting, conference or hack session).

A Sprint basically consists of a bunch of people getting together to discuss
some specific issues.
"""

__metaclass__ = type

__all__ = [
    'ISprint',
    'ISprintSet',
    ]

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import Datetime, Choice, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import (
    ContentNameField, LargeImageUpload, BaseImageUpload, SmallImageUpload)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.interfaces import IHasOwner, IHasSpecifications


class SprintNameField(ContentNameField):

    errormessage = _("%s is already in use by another sprint.")

    @property
    def _content_iface(self):
        return ISprint

    def _getByName(self, name):
        return getUtility(ISprintSet)[name]


class ISprint(IHasOwner, IHasSpecifications):
    """A sprint, or conference, or meeting."""

    name = SprintNameField(
        title=_('Name'), required=True, description=_('A unique name '
        'for this sprint, or conference, or meeting. This will part of '
        'the URL so pick something short. A single word is all you get.'),
        constraint=name_validator)
    displayname = Attribute('A pseudonym for the title.')
    title = TextLine(
        title=_('Title'), required=True, description=_("Please provide "
        "a title for this meeting. This will be shown in listings of "
        "meetings."))
    summary = Text(
        title=_('Summary'), required=True, description=_("A one-paragraph "
        "summary of the meeting plans and goals. Put the rest in a web "
        "page and link to it using the field below."))
    driver = Choice(title=_('Meeting Driver'), required=False,
        description=_('The person or team that will manage the agenda of '
        'this meeting. Use this if you want to delegate the approval of '
        'agenda items to somebody else.'), vocabulary='ValidPersonOrTeam')
    address = Text(
        title=_('Meeting Address'), required=False,
        description=_("The address of the meeting venue."))
    home_page = TextLine(
        title=_('Home Page'), required=False, description=_("A web page "
        "with further information about the event."))
    homepage_content = Text(
        title=_("Homepage Content"), required=False,
        description=_(
            "The content of this meeting's home page. Edit this and it "
            "will be displayed for all the world to see. It is NOT a wiki "
            "so you cannot undo changes."))
    emblem = SmallImageUpload(
        title=_("Emblem"), required=False,
        description=_(
            "A small image, max 16x16 pixels and 25k in file size, that can "
            "be used to refer to this meeting."))
    # This field should not be used on forms, so we use a BaseImageUpload here
    # only for documentation purposes.
    gotchi_heading = BaseImageUpload(
        title=_("Heading icon"), required=False,
        description=_(
            "An image, maximum 64x64 pixels, that will be displayed on "
            "the header of all pages related to this meeting. It should "
            "be no bigger than 50k in size."))
    gotchi = LargeImageUpload(
        title=_("Icon"), required=False,
        description=_(
            "An image, maximum 170x170 pixels, that will be displayed on "
            "this meeting's home page. It should be no bigger than 100k "
            "in size. "))
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
    
    def specificationLinks(status=None):
        """Return the SprintSpecification records matching the filter,
        quantity and sort given. The rules for filtering and sorting etc are
        the same as those for IHasSpecifications.specifications()
        """

    def getSpecificationLink(id):
        """Return the specification link for this sprint that has the given
        ID. We use the naked ID because there is no unique name for a spec
        outside of a single product or distro, and a sprint can cover
        multiple products and distros.
        """

    def acceptSpecificationLinks(idlist, decider):
        """Accept the given sprintspec items, and return the number of
        sprintspec items that remain proposed.
        """

    def declineSpecificationLinks(idlist, decider):
        """Decline the given sprintspec items, and return the number of
        sprintspec items that remain proposed.
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
            description=None, gotchi=None, gotchi_heading=None, emblem=None):
        """Create a new sprint."""

