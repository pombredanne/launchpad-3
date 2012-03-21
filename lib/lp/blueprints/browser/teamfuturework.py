# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Upcoming team work views."""

__metaclass__ = type

__all__ = [
    'TeamFutureWorkView',
    ]

from operator import itemgetter

from lp.services.webapp import (
    LaunchpadView,
    )

from datetime import datetime


class TeamFutureWorkView(LaunchpadView):
    """XXX"""

    @property
    def label(self):
        return self.context.displayname

    @property
    def page_title(self):
        return "Upcoming work for %s." % self.label

    @property
    def page_description(self):
        return "Work for %s in the near future." % self.label

    def overall_completion(self):
        # This is actually per-milestone and not overall.
        n_complete = 0
        total = 0
        for group in self.work_item_groups:
            for item in group.items:
                total += 1
                if item.is_complete:
                    n_complete += 1
        return total, n_complete

    @property
    def upcoming_bp_count(self):
        return len([1,2,3,4])

    @property
    def upcoming_wi_count(self):
        return len([1,2,3,4,5,6,7,8,9,0])

    @property
    def work_item_containers(self):
        result = self.context.getWorkItemsDueBefore(
            datetime(2050, 1, 1), self.user)
        return sorted(result.items(), key=itemgetter(0))
