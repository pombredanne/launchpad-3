# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser code for Distro Series Languages."""

__metaclass__ = type

__all__ = [
    'DistroSeriesLanguageNavigation',
    'DistroSeriesLanguageView',
    ]

from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.publisher import Navigation
from lp.translations.interfaces.distroserieslanguage import (
    IDistroSeriesLanguage)

class DistroSeriesLanguageView(LaunchpadView):
    """View class to render translation status for an `IDistroSeries`."""

    pofiles = None
    label = "Translatable templates"

    def initialize(self):
        self.form = self.request.form

        self.batchnav = BatchNavigator(
            self.context.distroseries.getCurrentTranslationTemplates(),
            self.request)

        self.pofiles = self.context.getPOFilesFor(
            self.batchnav.currentBatch())
        self.parent = self.context.distroseries.distribution

    @property
    def translation_group(self):
        return self.context.distroseries.distribution.translationgroup

    @property
    def translation_team(self):
        """Is there a translation team for this translation."""
        if self.translation_group is not None:
            team = self.translation_group.query_translator(
                self.context.language)
        else:
            team = None
        return team


class DistroSeriesLanguageNavigation(Navigation):
    """Navigation for `IDistroSeriesLanguage`."""
    usedfor = IDistroSeriesLanguage
