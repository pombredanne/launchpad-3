# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'RosettaApplicationView',
    'RosettaStatsView',
    'RosettaApplicationNavigation',
    'TranslationsMixin'
    ]

import httplib

from canonical.config import config

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IRequestPreferredLanguages, ICountry, ILaunchpadCelebrities,
    IRosettaApplication, ILanguageSet, ILaunchpadRoot, ITranslationGroupSet,
    IProjectSet, IProductSet, ITranslationImportQueue)
from canonical.launchpad import helpers
import canonical.launchpad.layers
from canonical.launchpad.webapp import (
    Navigation, redirection, stepto, canonical_url)
from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.cachedproperty import cachedproperty


class TranslationsMixin:
    """Translation mixin that provides language handling."""
    @property
    def translatable_languages(self):
        """Return a set of the Person's translatable languages."""
        english = getUtility(ILanguageSet)['en']
        languages = helpers.request_languages(self.request)
        if english in languages:
            languages.remove(english)
        return languages


class RosettaApplicationView(TranslationsMixin):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def ubuntu_translationseries(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        series = ubuntu.translation_focus
        if series is None:
            return ubuntu.currentseries
        else:
            return series

    def ubuntu_languages(self):
        langs = []
        series = self.ubuntu_translationseries
        for language in self.languages:
            langs.append(series.getDistroSeriesLanguageOrDummy(language))
        return langs

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return IRequestPreferredLanguages(self.request).getPreferredLanguages()

    @cachedproperty
    def batchnav(self):
        """Return a BatchNavigator for the list of translatable products."""
        products = getUtility(IProductSet)
        return BatchNavigator(products.getTranslatables(),
                              self.request)

    def rosettaAdminEmail(self):
        return config.rosetta.rosettaadmin.email


class RosettaStatsView:
    """A view class for objects that support IRosettaStats. This is mainly
    used for the sortable untranslated percentage."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sortable_untranslated(self):
        return '%06.2f' % self.context.untranslatedPercentage()


class RosettaApplicationNavigation(Navigation):

    usedfor = IRosettaApplication

    newlayer = canonical.launchpad.layers.TranslationsLayer

    # DEPRECATED: Support bookmarks to the old rosetta prefs page.
    redirection('prefs', '/+editmylanguages', status=httplib.MOVED_PERMANENTLY)

    @stepto('groups')
    def redirect_groups(self):
        """Redirect /translations/+groups to Translations root site."""
        target_url= canonical_url(
            getUtility(ILaunchpadRoot), rootsite='translations')
        return self.redirectSubTree(
            target_url + '+groups', status=301)

    @stepto('imports')
    def imports(self):
        return getUtility(ITranslationImportQueue)

    @stepto('projects')
    def projects(self):
        # DEPRECATED
        return getUtility(IProductSet)

    @stepto('products')
    def products(self):
        # DEPRECATED
        return getUtility(IProductSet)
