# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintAttendance."""

__metaclass__ = type
__all__ = [
    'SprintAttendanceAttendView',
    'SprintAttendanceRegisterView',
    ]

import datetime
import pytz

from canonical.launchpad import _
from canonical.launchpad.interfaces import ISprintAttendance
from canonical.launchpad.webapp import (
    LaunchpadFormView, action, canonical_url, custom_widget)
from canonical.widgets.date import DateTimeWidget


class BaseSprintAttendanceAddView(LaunchpadFormView):

    schema = ISprintAttendance
    custom_widget('time_starts', DateTimeWidget)
    custom_widget('time_ends', DateTimeWidget)

    def setUpWidgets(self):
        LaunchpadFormView.setUpWidgets(self)
        tz = pytz.timezone(self.context.time_zone)
        self.starts_widget = self.widgets['time_starts']
        self.ends_widget = self.widgets['time_ends']
        self.starts_widget.required_timezone = tz
        self.ends_widget.required_timezone = tz
        self.starts_widget.from_date = self.context.time_starts.date()
        self.starts_widget.to_date = self.context.time_ends.date()
        self.ends_widget.from_date = self.context.time_starts.date()
        self.ends_widget.to_date = self.context.time_ends.date()

    def validate(self, data):
        """Verify that the entered times are valid.

        We check that:
         * they depart after they arrive
         * they don't arrive after the end of the sprint
         * they don't depart before the start of the sprint
        """
        time_starts = data.get('time_starts')
        time_ends = data.get('time_ends')

        if time_starts and time_starts > self.context.time_ends:
            self.setFieldError(
                'time_starts',
                _('Choose an arrival time before the end of the meeting.'))
        if time_ends:
            if time_starts and time_ends < time_starts:
                self.setFieldError(
                    'time_ends',
                    _('The end time must be after the start time.'))
            elif time_ends < self.context.time_starts:
                self.setFieldError(
                    'time_ends', _('Choose a departure time after the '
                                   'start of the meeting.'))
            elif (time_ends.hour == 0 and time_ends.minute == 0 and
                  time_ends.second == 0):
                # We assume the user entered just a date, which gives them
                # midnight in the morning of that day, when they probably want
                # the end of the day.
                data['time_ends'] = min(
                    self.context.time_ends,
                    time_ends + datetime.timedelta(days=1, seconds=-1))

    def getDates(self, data):
        time_starts = data['time_starts']
        time_ends = data['time_ends']
        if (time_ends.hour == 0 and time_ends.minute == 0 and
            time_ends.second == 0):
            # We assume the user entered just a date, which gives them
            # midnight in the morning of that day, when they probably want
            # the end of the day.
            time_ends = time_ends + datetime.timedelta(days=1, seconds=-1)
        if time_starts < self.context.time_starts:
            # Can't arrive before the conference starts, we assume that you
            # meant to say you will get there at the beginning
            time_starts = self.context.time_starts
        if time_ends > self.context.time_ends:
            # Can't stay after the conference ends, we assume that you meant
            # to say you will leave at the end.
            time_ends = self.context.time_ends
        return time_starts, time_ends

    @property
    def next_url(self):
        return canonical_url(self.context)


class SprintAttendanceAttendView(BaseSprintAttendanceAddView):
    """A view used to register your attendance at a sprint."""

    field_names = ['time_starts', 'time_ends']

    @property
    def initial_values(self):
        for attendance in self.context.attendances:
            if attendance.attendee == self.user:
                return dict(time_starts=attendance.time_starts,
                            time_ends=attendance.time_ends)
        return {}

    @action(_('Register'), name='register')
    def register_action(self, action, data):
        time_starts, time_ends = self.getDates(data)
        self.context.attend(self.user, time_starts, time_ends)


class SprintAttendanceRegisterView(BaseSprintAttendanceAddView):
    """A view used to register someone else's attendance at a sprint."""

    field_names = ['attendee', 'time_starts', 'time_ends']

    @action(_('Register'), name='register')
    def register_action(self, action, data):
        time_starts, time_ends = self.getDates(data)
        self.context.attend(data['attendee'], time_starts, time_ends)
