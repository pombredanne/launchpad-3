from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute
from zope.schema import Int, Object, TextLine
from canonical.launchpad.fields import Title
from schoolbell.interfaces import ICalendar


class ILaunchpadCalendar(ICalendar):
    """Launchpad specific calendar.

    TODO: make it inherit IEditCalendar.
    """

    owner = Attribute("The person who can edit this calendar")

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

    def nextURL():
        """A URL to the 'next' calendar view (eg. tomorrow, next week, etc)."""
        pass
    def prevURL():
        """A URL to the 'previous' calendar view (eg. tomorrow, next
        week, etc)."""
        pass
    def dayViewURL():
        """A URL to switch to the day view.  Should be related to the time
        period currently being viewed."""
        pass
    def weekViewURL():
        """A URL to switch to the week view.  Should be related to the time
        period currently being viewed."""
        pass
    def monthViewURL():
        """A URL to switch to the month view.  Should be related to the time
        period currently being viewed."""
        pass
    def yearViewURL():
        """A URL to switch to the year view.  Should be related to the time
        period currently being viewed."""
        pass

class ICalendarDayView(ICalendarView):
    """A day view of a calendar."""

    pass

class ICalendarWeekView(ICalendarView):
    """A week view of a calendar."""
    
