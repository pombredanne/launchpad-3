# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintAttendance."""

__metaclass__ = type
__all__ = [
    'SprintAttendanceAddView',
    ]

import datetime

from zope.component import getUtility

from canonical.launchpad.interfaces import ISprintAttendance, ILaunchBag

from canonical.launchpad.webapp import canonical_url, GeneralFormView


class SprintAttendanceAddView(GeneralFormView):

    def process(self, attendee, time_starts, time_ends):
        if time_ends.hour == 0 and time_ends.minute == 0 and \
            time_ends.second == 0:
            # We assume the user entered just a date, which gives them
            # midnight in the morning of that day, when they probably want
            # the end of the day
            time_ends = time_ends + datetime.timedelta(0, 0, 0, 0, 59, 23)
        if time_starts >= time_ends:
            return 'Attendee should come before going!'
        if time_starts < self.context.time_starts:
            # Can't arrive before the conference starts, we assume that you
            # meant to say you will get there at the beginning
            time_starts = self.context.time_starts
        if time_starts > self.context.time_ends:
            # You do need to show up before the meeting ends
            return 'Choose an arrival time before the end of the meeting'
        if time_ends > self.context.time_ends:
            time_ends = self.context.time_ends
        self._nextURL = canonical_url(self.context)
        return self.context.attend(attendee, time_starts, time_ends)

