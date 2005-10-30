# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Sprint Attendance interfaces."""

__metaclass__ = type

__all__ = [
    'ISprintAttendance',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')


class ISprintAttendance(Interface):
    """An attendance of a person at a sprint."""

    attendee = Choice(title=_('Attendee'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')
    sprint = Choice(title=_('The Sprint'), required=True, readonly=True,
        vocabulary='Sprint',
        description=_("Select the meeting from the list presented above."))
    time_starts = Datetime(title=_('Starting At'), required=True,
        description=_("The date and time you will be arriving and "
        "available for sessions during the sprint. Use a time and date "
        "in UTC (GMT). For example: 2005-10-12 13:30:00"))
    time_ends = Datetime(title=_('Finishing At'), required=True,
        description=_("The date and time you will be departing and "
        "hence no longer available for sessions during the sprint. "
        "Again, use UTC."))

