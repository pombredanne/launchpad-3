# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View for daily builds listings."""

__metaclass__ = type

__all__ = [
    'CompletedDailyBuildsView',
    ]

from canonical.config import config
from canonical.launchpad.browser.feeds import FeedsMixin
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator


class CompletedDailyBuildsView(LaunchpadView, FeedsMixin):

    @property
    def page_title(self):
        return 'Completed Daily Recipe Builds'

    def initialize(self):
        self.dailybuilds = self.context.findCompletedDailyBuilds()
        self.batchnav = BatchNavigator(
            self.dailybuilds, self.request,
            size=config.launchpad.recipebuildlisting_batch_size)
