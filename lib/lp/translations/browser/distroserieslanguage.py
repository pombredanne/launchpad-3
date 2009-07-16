# Copyright 2004-2009 Canonical Ltd.  All rights reserved.

"""Browser code for Distro Series Languages."""

__metaclass__ = type

__all__ = ['DistroSeriesLanguageView']

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator


class DistroSeriesLanguageView(LaunchpadView):
    """View class to render translation status for an `IDistroSeries`."""

    pofiles = None

    def initialize(self):
        self.form = self.request.form

        self.batchnav = BatchNavigator(
            self.context.distroseries.getCurrentTranslationTemplates(),
            self.request)

        self.pofiles = self.context.getPOFilesFor(
            self.batchnav.currentBatch())
