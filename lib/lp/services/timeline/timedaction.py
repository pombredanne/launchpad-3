# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Time a single categorised action."""


__all__ = ['TimedAction']

__metaclass__ = type


import datetime

import pytz


UTC = pytz.utc


class TimedAction:
    """An individual action which has been timed.

    :ivar timeline: The timeline that this action took place within.
    :ivar start: A datetime object with tz for the start of the action.
    :ivar duration: A timedelta for the duration of the action. None for
        actions which have not completed.
    :ivar category: The category of the action. E.g. "sql".
    :ivar detail: The detail about the action. E.g. "SELECT COUNT(*) ..."
    """

    def __init__(self, category, detail, timeline=None):
        """Create a TimedAction.

        New TimedActions have a start but no duration.

        :param category: The category for the action.
        :param detail: The detail about the action being timed.
        :param timeline: The timeline for the action.
        """
        self.start = datetime.datetime.now(UTC)
        self.duration = None
        self.category = category
        self.detail = detail
        self.timeline = timeline

    def __repr__(self):
        return "<TimedAction %s[%s]>" % (self.category, self.detail[:20])

    def logTuple(self):
        """Return a 4-tuple suitable for errorlog's use."""
        offset = self._td_to_ms(self.start - self.timeline.baseline)
        if self.duration is None:
            # This action wasn't finished: pretend it has finished now
            # (even though it hasn't). This is pretty normal when action ends
            # are recorded by callbacks rather than stack-like structures. E.g.
            # storm tracers in launchpad:
            # log-trace START : starts action
            # timeout-trace START : raises 
            # log-trace FINISH is never called.
            length = self._td_to_ms(self._interval_to_now())
        else:
            length = self._td_to_ms(self.duration)
        return (offset, offset + length, self.category, self.detail)

    def _td_to_ms(self, td):
        """Tweak on a backport from python 2.7"""
        return (td.microseconds + (
            td.seconds + td.days * 24 * 3600) * 10**6) / 10**3

    def finish(self):
        """Mark the TimedAction as finished."""
        self.duration = self._interval_to_now()

    def _interval_to_now(self):
        return datetime.datetime.now(UTC) - self.start
