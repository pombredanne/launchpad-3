# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser code for Product Series Languages."""

__metaclass__ = type

__all__ = ['ProductSeriesLanguageView']

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator


class ProductSeriesLanguageView(LaunchpadView):
    """View class to render translation status for an `IProductSeries`."""

    pofiles = None

    def initialize(self):
        self.form = self.request.form

        self.batchnav = BatchNavigator(
            self.context.productseries.getCurrentTranslationTemplates(),
            self.request)

        self.pofiles = self.context.getPOFilesFor(
            self.batchnav.currentBatch())

    @cachedproperty
    def translation_group(self):
        return self.context.productseries.product.translationgroup

    @cachedproperty
    def translation_team(self):
        """Is there a translation team for this translation."""
        if self.translation_group is not None:
            team = self.translation_group.query_translator(
                self.context.language)
        else:
            team = None
        return team
