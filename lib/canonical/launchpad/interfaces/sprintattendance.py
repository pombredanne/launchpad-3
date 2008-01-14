# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Sprint Attendance interfaces."""

__metaclass__ = type

__all__ = [
    'ISprintAttendance',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime
from canonical.launchpad import _


class ISprintAttendance(Interface):
    """An attendance of a person at a sprint."""

    attendee = Choice(title=_('Attendee'), required=True,
        vocabulary='ValidPersonOrTeam')
    sprint = Choice(title=_('The Sprint'), required=True,
        vocabulary='Sprint',
        description=_("Select the meeting from the list presented above."))
    time_starts = Datetime(title=_('Starting At'), required=True,
        description=_("The date and time of arrival and "
        "availability for sessions during the sprint. The time is "
        "interpreted according to the sprint's local time"))
    time_ends = Datetime(title=_('Finishing At'), required=True,
        description=_("The date and time of departure. Again, use "
        "the sprint's local time"))

