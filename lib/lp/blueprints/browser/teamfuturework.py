# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Upcoming team work views."""

__metaclass__ = type

__all__ = [
    'TeamFutureWorkView',
    ]
from lp.services.webapp import (
    LaunchpadView,
    )


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

    @property
    def upcoming_bp_count(self):
        return len([1,2,3,4])

    @property
    def upcoming_wi_count(self):
        return len([1,2,3,4,5,6,7,8,9,0])

    @property
    def blueprints(self):
        # XXX this didn't work. spec for a team does not give specs for all team members
        return self.context.valid_specifications
