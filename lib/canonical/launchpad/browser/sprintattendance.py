# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintAttendance."""

__metaclass__ = type
__all__ = [
    'SprintAttendanceAddView',
    ]

import datetime

from canonical.launchpad.interfaces import validate_date_interval

from canonical.launchpad.webapp import canonical_url, GeneralFormView

from canonical.launchpad import _


class SprintAttendanceAddView(GeneralFormView):

    def validate(self, form_values):
        """Verify if the entered dates are valid.

        valid dates mean:
        - time_starts precedes time_ends;
        - time_starts precedes self.context.time_ends;
        - self.context.time_starts precedes time_ends.

        """
        time_starts = form_values['time_starts']
        time_ends = form_values['time_ends']
        msg = _("The end time must be after the start time.")
        validate_date_interval(time_starts, time_ends, error_msg=msg)
        msg = _("Choose an arrival time before the end of the meeting.")
        validate_date_interval(
            time_starts, self.context.time_ends, error_msg=msg)
        msg = _("Choose a departure time after the start of the meeting.")
        validate_date_interval(
            self.context.time_starts, time_ends, error_msg=msg)

    def process(self, attendee, time_starts, time_ends):
        if time_ends.hour == 0 and time_ends.minute == 0 and \
            time_ends.second == 0:
            # We assume the user entered just a date, which gives them
            # midnight in the morning of that day, when they probably want
            # the end of the day
            time_ends = time_ends + datetime.timedelta(0, 0, 0, 0, 59, 23)
        if time_starts < self.context.time_starts:
            # Can't arrive before the conference starts, we assume that you
            # meant to say you will get there at the beginning
            time_starts = self.context.time_starts
        if time_ends > self.context.time_ends:
            # Can't stay after the conference ends, we assume that you meant
            # to say you will leave at the end.
            time_ends = self.context.time_ends
        self._nextURL = canonical_url(self.context)
        return self.context.attend(attendee, time_starts, time_ends)

