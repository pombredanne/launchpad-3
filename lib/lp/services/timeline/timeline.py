# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Coordinate a sequence of non overlapping TimedActionss."""

__all__ = ['Timeline']

__metaclass__ = type

import datetime

from pytz import utc as UTC

from timedaction import TimedAction


class OverlappingActionError(Exception):
    """A new action was attempted without finishing the prior one."""
    # To make analysis easy we do not permit overlapping actions: each
    # action that is being timed and accrued must complete before the next
    # is started. This means, for instance, that sending mail cannot do SQL
    # queries, as both are timed and accrued. OTOH it makes analysis and
    # serialisation of timelines simpler, and for the current use cases in 
    # Launchpad this is sufficient. This constraint should not be considered
    # sacrosanct - if, in future, we desire timelines with overlapping actions,
    # as long as the OOPS analysis code is extended to generate sensible
    # reports in those situations, this can be changed.


class Timeline:
    """A sequence of TimedActions.

    This is used for collecting expensive/external actions inside Launchpad
    requests.

    :ivar actions: The actions.
    :ivar baseline: The point the timeline starts at.
    """

    def __init__(self, actions=None):
        """Create a Timeline.
        
        :param actions: An optional object to use to store the timeline. This
            must implement the list protocol.
        """
        if actions is None:
            actions = []
        self.actions = actions
        self.baseline = datetime.datetime.now(UTC)

    def start(self, category, detail):
        """Create a new TimedAction at the end of the timeline.

        :param category: the category for the action.
        :param detail: The detail for the action.
        :return: A TimedAction for that category and detail.
        """
        result = TimedAction(category, detail, self)
        if self.actions and self.actions[-1].duration is None:
            raise OverlappingActionError(self.actions[-1], result)
        self.actions.append(result)
        return result
