# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Time a single categorised action."""


__all__ = ['TimedAction']

__metaclass__ = type


import datetime
import time

import pytz


UTC = pytz.utc


class TimedAction:
    """An individual action which has been timed.

    ;ivar start: A datetime object with tz for the start of the action.
    :ivar duration: A timedelta for the duration of the action. None for
        actions which have not completed.
    :ivar category: The category of the action. E.g. "sql".
    :ivar detail: The detail about the action. E.g. "SELECT COUNT(*) ..."
    """

    def __init__(self, category, detail):
        """Create a TimedAction.

        New TimedActions have a start but no duration.

        :param category: The category for the action.
        :param detail: The detail about the action being timed.
        """
        self.start = datetime.datetime.now(UTC)
        self.duration = None
        self.category = category
        self.detail = detail

    def finish(self):
        """Mark the TimedAction as finished."""
        self.duration = datetime.datetime.now(UTC) - self.start
