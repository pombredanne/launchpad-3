# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser code for Product Series Languages."""

__metaclass__ = type

__all__ = ['ProductSeriesLanguageView']

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator


class ProductSeriesLanguageView(LaunchpadView):
    """View class to render translation status for an IProductSeries."""

    def initialize(self):
        self.form = self.request.form

        # Setup batching for this page.
        self.batchnav = BatchNavigator(
            self.context.pofiles_or_dummies,
            self.request)

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
