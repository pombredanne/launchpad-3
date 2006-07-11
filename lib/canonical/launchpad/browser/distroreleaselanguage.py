# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser code for Distro Release Languages."""

__metaclass__ = type

__all__ = ['DistroReleaseLanguageView']

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator


class DistroReleaseLanguageView(LaunchpadView):
    """View class to render translation status for an IDistroRelease."""

    def initialize(self):
        self.form = self.request.form

        # Setup batching for this page.
        self.batchnav = BatchNavigator(
            self.context.po_files_or_dummies, self.request)
