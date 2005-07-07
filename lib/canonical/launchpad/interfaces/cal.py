# Copyright 2005 Canonical Ltd. All rights reserved.

"""Calendar-related interfaces."""

__metaclass__ = type

__all__ = [
    'ILaunchpadCalendar',
    'ILaunchpadMergedCalendar',
    'ICalendarOwner',
    'ICalendarSet',
    'ICalendarEventSet',
    'ICalendarSubscriptionSet',
    'ICalendarDay',
    'ICalendarWeek',
    'ICalendarMonth',
    'ICalendarYear',
    ]

from zope.i18nmessageid import MessageIDFactory
from zope.interface import Interface, Attribute
from zope.schema import Int, Object, TextLine

from schoolbell.interfaces import IEditCalendar

from canonical.launchpad.fields import Title
from canonical.launchpad.interfaces.launchpad import IHasOwner

_ = MessageIDFactory('launchpad')

class ILaunchpadCalendar(IEditCalendar, IHasOwner):
    """Launchpad specific calendar.
    """

    id = Int(title=_("ID"), required=False)

    title = Title(
        title=_('Calendar title'), required=True,
        description=_("""The title of the calendar is a short
        description of the calendar that can be used to
        identify a specific calendar."""))

    revision = Int(
        title=_('Revision'), readonly=True,
        description=_("""The calendar revision is incremented
        each time the calendar is changed."""))

    parent = Attribute(_("""The parent object that owns the calendar."""))

class ILaunchpadMergedCalendar(Interface):
    """Marker interface to identify the user's merged calendar."""

class ICalendarOwner(Interface):
    """An object that has a calendar."""

    calendar = Object(
        title=_('Calendar'),
        schema=ILaunchpadCalendar,
        description=_("""The calendar for this object."""))

    def getOrCreateCalendar():
        """Get the calendar.  Create it if it doesn't exist."""

class ICalendarSet(Interface):
    def __getitem__(id):
        """Get a calendar by ID."""

class ICalendarEventSet(Interface):
    def __getitem__(id):
        """Get an event by ID."""

class ICalendarSubscriptionSet(Interface):
    """A list of calendars a user is subscribed to."""
    owner = Attribute(_("The owner of the subscriptions"))

    def __iter__():
        """Iterate over the calendars the user is subscribed to."""

    def __contains__(calendar):
        """Returns True if the calendar has been subscribed to."""

    def subscribe(calendar):
        """Subscribe to a calendar."""

    def unsubscribe(calendar):
        """Unsubscribe from a calendar.  Raises an exception if the
        calendar hasn't been subscribed to."""

    def getColour(calendar):
        """Get the colour used to display events from this calendar"""

    def setColour(calendar, colour):
        """Set the colour used to display events from this calendar"""        

class ICalendarDay(Interface):
    """Represents a particular day of events in a calendar"""
    calendar = Object(
        title=_('Calendar'),
        schema=ILaunchpadCalendar,
        description=_("""The calendar"""))
    name = TextLine(
        title=_('Name'), required=True, readonly=True,
        description=_("""A string describing the day"""))
    year = Int(
        title=_('Year'), required=True, readonly=True,
        description=_("""The year to display."""))
    month = Int(
        title=_('Month'), required=True, readonly=True,
        description=_("""The month number to display."""))
    day = Int(
        title=_('Day'), required=True, readonly=True,
        description=_("""The day number to display."""))

class ICalendarWeek(Interface):
    """Represents a particular week of events in a calendar"""
    calendar = Object(
        title=_('Calendar'),
        schema=ILaunchpadCalendar,
        description=_("""The calendar"""))
    name = TextLine(
        title=_('Name'), required=True, readonly=True,
        description=_("""A string describing the week"""))
    year = Int(
        title=_('Year'), required=True, readonly=True,
        description=_("""The year to display."""))
    week = Int(
        title=_('Week'), required=True, readonly=True,
        description=_("""The ISO week number to display."""))

class ICalendarMonth(Interface):
    """Represents a particular week of events in a calendar"""
    calendar = Object(
        title=_('Calendar'),
        schema=ILaunchpadCalendar,
        description=_("""The calendar"""))
    name = TextLine(
        title=_('Name'), required=True, readonly=True,
        description=_("""A string describing the month"""))
    year = Int(
        title=_('Year'), required=True, readonly=True,
        description=_("""The year to display."""))
    month = Int(
        title=_('Month'), required=True, readonly=True,
        description=_("""The month number to display."""))

class ICalendarYear(Interface):
    """Represents a particular year of events in a calendar"""
    calendar = Object(
        title=_('Calendar'),
        schema=ILaunchpadCalendar,
        description=_("""The calendar"""))
    name = TextLine(
        title=_('Name'), required=True, readonly=True,
        description=_("""A string describing the year"""))
    year = Int(
        title=_('Year'), required=True, readonly=True,
        description=_("""The year to display."""))
