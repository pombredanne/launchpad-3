# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Time an action which calls other timed actions."""


__all__ = ['NestingTimedAction']

__metaclass__ = type


import datetime

from timedaction import TimedAction


class NestingTimedAction(TimedAction):
    """A variation of TimedAction which creates a nested environment.
    
    This is done by recording two 0 length timed actions in the timeline:
    one at the start of the action and one at the end, with -start and
    -stop appended to their categories.

    See `TimedAction` for more information.
    """

    def _init(self):
        self.duration = datetime.timedelta()
        self._category = self.category
        self.category = self._category + '-start'

    def finish(self):
        """Mark the TimedAction as finished."""
        end = self.timeline.start(self._category + '-stop', self.detail)
        end.duration = datetime.timedelta()
