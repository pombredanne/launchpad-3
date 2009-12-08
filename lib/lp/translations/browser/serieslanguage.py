# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser code for Distro Series Languages."""

__metaclass__ = type

__all__ = [
    'DistroSeriesLanguageNavigation',
    'DistroSeriesLanguageView',
    'ProductSeriesLanguageNavigation',
    'ProductSeriesLanguageView',
    ]

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.webapp.publisher import Navigation
from lp.translations.interfaces.distroserieslanguage import (
    IDistroSeriesLanguage)
from lp.translations.interfaces.translationsperson import (
    ITranslationsPerson)
from lp.translations.interfaces.translationgroup import (
    TranslationPermission)
from lp.translations.interfaces.productserieslanguage import (
    IProductSeriesLanguage)


class SeriesLanguageView(LaunchpadView):
    """View class to render translation status for an `IDistroSeries`
    and `IProductSeries`"""

    pofiles = None
    label = "Translatable templates"
    series = None
    parent = None
    translationgroup = None

    def initialize(self):
        self.form = self.request.form

        self.batchnav = BatchNavigator(
            self.series.getCurrentTranslationTemplates(),
            self.request)

        self.pofiles = self.context.getPOFilesFor(
            self.batchnav.currentBatch())

    @cachedproperty
    def translation_group(self):
        """Is there a translation group for these translations."""
        return self.translationgroup

    @cachedproperty
    def translation_team(self):
        """Is there a translation team for these translations."""
        if self.translation_group is not None:
            team = self.translation_group.query_translator(
                self.context.language)
        else:
            team = None
        return team

    @property
    def show_not_logged_in(self):
        """Should we display a notice that user is not logged in?"""
        return self.user is None

    @property
    def show_no_license(self):
        """Should we display a notice that licence was not accepted?"""
        if self.show_not_logged_in:
            return False
        translations_person = ITranslationsPerson(self.user)
        return not translations_person.translations_relicensing_agreement

    @property
    def show_full_edit(self):
        """Should we display a notice that user is not logged in?"""
        if (self.show_not_logged_in or 
            self.show_no_license):
            return False

        sample_pofile = self.pofiles[0]
        if sample_pofile is None:
            return False

        return sample_pofile.canEditTranslations(self.user)

    @property
    def show_can_suggest(self):
        """Should we display a notice that user is not logged in?"""
        if (self.show_not_logged_in or 
            self.show_no_license or
            self.show_full_edit):
            return False

        sample_pofile = self.pofiles[0]
        if sample_pofile is None:
            return False

        return sample_pofile.canAddSuggestions(self.user)

    @property
    def show_only_managers(self):
        """Should we display a notice that user is not logged in?"""
        if (self.show_not_logged_in or 
            self.show_no_license or
            self.show_full_edit or
            self.show_can_suggest):
            return False

        sample_pofile = self.pofiles[0]
        if sample_pofile is None:
            return False

        if (sample_pofile.translationpermission == TranslationPermission.CLOSED):
            return True
        else:
            return False

    @property
    def show_no_managers(self):
        """Should we display a notice that user is not logged in?"""
        if (self.show_not_logged_in or
            self.show_no_license or
            self.show_full_edit or
            self.show_can_suggest or
            self.show_only_managers):
            return False
        if self.translation_team is None:
            return True
        else:
            return False


class DistroSeriesLanguageView(SeriesLanguageView, LaunchpadView):
    """View class to render translation status for an `IDistroSeries`."""

    def initialize(self):
        self.series =  self.context.distroseries
        SeriesLanguageView.initialize(self)
        self.parent = self.series.distribution
        self.translationgroup = self.series.distribution.translationgroup

class ProductSeriesLanguageView(SeriesLanguageView, LaunchpadView):
    """View class to render translation status for an `IProductSeries`."""

    def initialize(self):
        self.series =  self.context.productseries
        SeriesLanguageView.initialize(self)
        self.context.recalculateCounts()
        self.parent = self.series.product
        self.translationgroup = self.series.product.translationgroup


class DistroSeriesLanguageNavigation(Navigation):
    """Navigation for `IDistroSeriesLanguage`."""
    usedfor = IDistroSeriesLanguage


class ProductSeriesLanguageNavigation(Navigation):
    """Navigation for `IProductSeriesLanguage`."""
    usedfor = IProductSeriesLanguage
