from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute
from zope.schema import Int, Bool, Object, TextLine, Date, Datetime
from canonical.launchpad.fields import Title, TimeInterval
from schoolbell.interfaces import IEditCalendar


class ILaunchpadCalendar(IEditCalendar):
    """Launchpad specific calendar.

    TODO: make it inherit IEditCalendar.
    """

    owner = Attribute(_("The person who can edit this calendar"))

    title = Title(
                  title=_('Calendar title'), required=True,
                  description=_("""The title of the calendar is a short
                  description of the calendar that can be used to
                  identify a specific calendar.""")
                  )

    revision = Int(
                   title=_('Revision'), readonly=True,
                   description=_("""The calendar revision is incremented
                   each time the calendar is changed.""")
                   )


class ICalendarOwner(Interface):
    """An object that has a calendar."""

    calendar = Object(
        title=_('Calendar'),
        schema=ILaunchpadCalendar,
        description=_("""The calendar for this object."""))


class ICalendarView(Interface):
    """A view of the calendar."""

    calendar = Object(
        title=_('Calendar'),
        schema=ILaunchpadCalendar,
        description=_("""The calendar for this view."""))
    datestring = TextLine(
        title=_('Calendar View Date'), required=True, readonly=True,
        description=_("""A string describing the date range displayed
        by this view."""))

    nextURL = TextLine(
        title=_('The next page'), required=True, readonly=True,
        description=_("""A URL to the 'next' calendar view
        (eg. tomorrow, next week, etc)."""))
    prevURL = TextLine(
        title=_('The previous page'), required=True, readonly=True,
        description=_("""A URL to the 'previous' calendar view
        (eg. tomorrow, next week, etc)."""))

    dayViewURL = TextLine(
        title=_('The day view'), required=True, readonly=True,
        description=_("""A URL to switch to the day view.  Should be
        related to the time period currently being viewed."""))
    weekViewURL = TextLine(
        title=_('The week view'), required=True, readonly=True,
        description=_("""A URL to switch to the week view.  Should be
        related to the time period currently being viewed."""))
    monthViewURL = TextLine(
        title=_('The month view'), required=True, readonly=True,
        description=_("""A URL to switch to the month view.  Should be
        related to the time period currently being viewed."""))
    yearViewURL = TextLine(
        title=_('The year view'), required=True, readonly=True,
        description=_("""A URL to switch to the year view.  Should be
        related to the time period currently being viewed."""))


class ICalendarDayView(ICalendarView):
    """A day view of a calendar."""

class ICalendarWeekView(ICalendarView):
    """A week view of a calendar."""
    days = Attribute(_("A list of information about days of the week"))
    layout = Attribute(_("The layout of days in the week"))
    rowspans = Attribute(_("Rowspans for days in the week"))

class ICalendarMonthView(ICalendarView):
    """A month view of a calendar."""
    daynames = Attribute(_("Translated day names"))
    days = Attribute(_("An array of days in the month"))
    layout = Attribute(_("The layout of days in the month"))

class ICalendarYearView(ICalendarView):
    """A year view of a calendar."""
    daynames = Attribute(_("Translated day names"))
    months = Attribute(_("An array of month structures"))
    layout = Attribute(_("The layout of months in the year"))

class ICalendarMonthInfo(Interface):
    """Information about a particular month, used by the year view."""
    monthname = TextLine(
        title=_("Month name"),
        description=_("The name of the month"))
    days = Attribute(_("An array of the days in this month"))
    layout = Attribute(_("The layout of days in this month"))

class ICalendarDayInfo(Interface):
    """Information about a particular day, used by the various
    calendar views."""
    date = Date(
        title=_("Date"), required=False,
        description=_("The date this refers object refers to"))
    dayname = TextLine(
        title=_("Day name"),
        description=_("The name of this day"))
    dayURL = TextLine(
        title=_("Day URL"),
        description=_("A URL referring to this particular day"))
    hasEvents = Bool(
        title=_("Whether the day has events"),
        description=_("whether events occur on this day"))
    events = Attribute(_("The events occurring on this day"))

class ICalendarEventInfo(Interface):
    """Information about an event, used by the calendar views."""
    event = Object(
        title=_('Event'),
        schema=ILaunchpadCalendar,
        description=_("""The event."""))
    dtstart = Datetime(
        title=_("Start date"), required=False,
        description=_("The event start time in local time"))
    timestring = TextLine(
        title=_("The event start time as a string"))


class ICalendarEventAddForm(Interface):
    """Schema for the New Calendar Event form."""

    title = TextLine(
        title=_("Title"), required=True,
        description=_("""Title of the event"""))

    location = TextLine(
        title=_("Location"), required=False,
        description=_("""Location of the event"""))

    dtstart = Datetime(
        title=_("Start"), required=True,
        description=_("""Date and time when the event starts."""))

    duration = TimeInterval(
        title=_("Duration"), required=True,
        description=_("""Duration of the event."""))

    # TODO: recurrence
