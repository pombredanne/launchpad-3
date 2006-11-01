# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Views for SprintAttendance."""

__metaclass__ = type
__all__ = [
    'SprintAttendanceAttendView',
    'SprintAttendanceRegisterView',
    ]

import datetime

from canonical.launchpad import _
from canonical.launchpad.interfaces import ISprintAttendance
from canonical.launchpad.webapp import (
    LaunchpadFormView, action, canonical_url, custom_widget)
from canonical.widgets.textwidgets import LocalDateTimeWidget


class BaseSprintAttendanceAddView(LaunchpadFormView):

    def setUpWidgets(self):
        LaunchpadFormView.setUpWidgets(self)
        tz = self.context.time_zone
        self.widgets['time_starts'].timeZoneName = tz
        self.widgets['time_ends'].timeZoneName = tz

    def validate(self, data):
        """Verify that the entered times are valid.

        We check that:
         * they depart after they arrive
         * they don't arrive before the start of the sprint
         * they don't depart after the end of the sprint
        """
        time_starts = data.get('time_starts')
        time_ends = data.get('time_ends')

        if time_starts and time_starts < self.context.time_starts:
            self.setFieldError('time_starts',
                               _('Choose an arrival time before the end '
                                 'of the meeting.'))
        if time_ends:
            if time_starts and time_ends < time_starts:
                self.setFieldError('time_ends',
                                   _('The end time must be after the '
                                     'start time.'))
            elif time_ends > self.context.time_ends:
                self.setFieldError('time_ends',
                                   _('Choose a departure time after the '
                                     'start of the meeting.'))
            elif (time_ends.hour == 0 and time_ends.minute == 0 and
                  time_ends.second == 0):
                # We assume the user entered just a date, which gives them
                # midnight in the morning of that day, when they probably want
                # the end of the day.
                data['time_ends'] = min(
                    self.context.time_ends,
                    time_ends + datetime.timedelta(days=1, seconds=-1))


class SprintAttendanceAttendView(BaseSprintAttendanceAddView):
    """A view used to register your attendance at a sprint."""
                
    schema = ISprintAttendance
    field_names = ['time_starts', 'time_ends']
    custom_widget('time_starts', LocalDateTimeWidget)
    custom_widget('time_ends', LocalDateTimeWidget)

    @action(_('Register'), name='register')
    def register_action(self, action, data):
        self.context.attend(self.user, data['time_starts'], data['time_ends'])

    @property
    def next_url(self):
        return canonical_url(self.context)


class SprintAttendanceRegisterView(BaseSprintAttendanceAddView):
    """A view used to register someone else's attendance at a sprint."""

    schema = ISprintAttendance
    field_names = ['attendee', 'time_starts', 'time_ends']
    custom_widget('time_starts', LocalDateTimeWidget)
    custom_widget('time_ends', LocalDateTimeWidget)

    @action(_('Register'), name='register')
    def register_action(self, action, data):
        self.context.attend(data['attendee'], data['time_starts'], data['time_ends'])

    @property
    def next_url(self):
        return canonical_url(self.context)
