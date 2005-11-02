# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintAttendance."""

__metaclass__ = type
__all__ = [
    'SprintAttendanceAddView',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import ISprintAttendance, ILaunchBag

from canonical.launchpad.webapp import canonical_url, GeneralFormView


class SprintAttendanceAddView(GeneralFormView):

    def process(self, attendee, time_starts, time_ends):
        if time_starts >= time_ends:
            return 'Attendee should come before going!'
        if time_starts < self.context.time_starts:
            time_starts = self.context.time_starts
        if time_ends > self.context.time_ends:
            time_ends = self.context.time_ends
        self._nextURL = canonical_url(self.context)
        return self.context.attend(attendee, time_starts, time_ends)

