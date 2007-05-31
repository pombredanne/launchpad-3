# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser code for Distro Series Languages."""

__metaclass__ = type

__all__ = ['DistroSeriesLanguageView']

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator


class DistroSeriesLanguageView(LaunchpadView):
    """View class to render translation status for an IDistroSeries."""

    def initialize(self):
        self.form = self.request.form

        # Setup batching for this page.
        self.batchnav = BatchNavigator(
            self.context.po_files_or_dummies, self.request)
