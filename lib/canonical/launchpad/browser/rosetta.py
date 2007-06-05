# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'RosettaApplicationView',
    'RosettaStatsView',
    'RosettaApplicationNavigation'
    ]

import httplib

from canonical.config import config

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IRequestPreferredLanguages, ICountry, ILaunchpadCelebrities,
    IRosettaApplication, ILaunchpadRoot, ITranslationGroupSet, IProjectSet,
    IProductSet, ITranslationImportQueue)
from canonical.launchpad import helpers
import canonical.launchpad.layers
from canonical.launchpad.webapp import (
    Navigation, redirection, stepto, canonical_url)
from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.cachedproperty import cachedproperty

class RosettaApplicationView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def languages(self):
        return helpers.request_languages(self.request)

    @property
    def ubuntu_translationrelease(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        release = ubuntu.translation_focus
        if release is None:
            return ubuntu.currentrelease
        else:
            return release

    def ubuntu_languages(self):
        langs = []
        release = self.ubuntu_translationrelease
        for language in self.languages:
            langs.append(release.getDistroReleaseLanguageOrDummy(language))
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
