from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from zope.interface import Interface, Attribute
from zope.schema import Int
from canonical.launchpad.fields import Title

class ICalendarOwner(Interface):
    """An object that has a calendar."""

    calendar = Attribute("The calendar for this object.")

class ILaunchpadCalendar(Interface):
    """Launchpad specific calendar attributes."""
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
    
