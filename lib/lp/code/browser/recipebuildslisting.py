# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View for daily builds listings."""

__metaclass__ = type

__all__ = [
    'CompletedDailyBuildsView',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator
from lp.code.interfaces.recipebuild import IRecipeBuildRecordSet


class CompletedDailyBuildsView(LaunchpadView):

    @property
    def page_title(self):
        return 'Recently Completed Daily Recipe Builds'

    def initialize(self):
        recipe_build_set = getUtility(IRecipeBuildRecordSet)
        self.dailybuilds = recipe_build_set.findCompletedDailyBuilds()
        self.batchnav = BatchNavigator(self.dailybuilds, self.request)
