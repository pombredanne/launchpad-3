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
    def blueprints(self):
        return self.context.valid_specifications
