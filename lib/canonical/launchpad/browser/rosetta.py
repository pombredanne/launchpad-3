# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

__all__ = [
    'RosettaApplicationView',
    'RosettaStatsView',
    'RosettaPreferencesView',
    'RosettaApplicationNavigation'
    ]

from sets import Set

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ILanguageSet, ILaunchBag, IRequestPreferredLanguages, ICountry,
    ILaunchpadCelebrities, IRosettaApplication, ITranslationGroupSet,
    IProjectSet, IProductSet, ITranslationImportQueue)
from canonical.launchpad import helpers
import canonical.launchpad.layers
from canonical.launchpad.webapp import Navigation, stepto, LaunchpadView


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


class RosettaStatsView:
    """A view class for objects that support IRosettaStats. This is mainly
    used for the sortable untranslated percentage."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sortable_untranslated(self):
        return '%06.2f' % self.context.untranslatedPercentage()


class RosettaPreferencesView(LaunchpadView):
    def processForm(self):
        """Process a form if it was submitted and prepare notifications."""
        if (self.request.method == "POST" and
            "SAVE-LANGS" in self.request.form):
            self.submitLanguages()

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return IRequestPreferredLanguages(self.request).getPreferredLanguages()

    def visible_checked_languages(self):
        return self.user.languages

    def visible_unchecked_languages(self):
        common_languages = getUtility(ILanguageSet).common_languages
        return sorted(set(common_languages) - set(self.user.languages),
                      key=lambda x: x.englishname)

    def getRedirectionURL(self):
        request = self.request
        referrer = request.getHeader('referer')
        if referrer and referrer.startswith(request.getApplicationURL()):
            return referrer
        else:
            return ''

    def submitLanguages(self):
        '''Process a POST request to the language preference form.

        This list of languages submitted is compared to the the list of
        languages the user has, and the latter is matched to the former.
        '''

        all_languages = getUtility(ILanguageSet)
        old_languages = self.user.languages
        new_languages = []

        for key in all_languages.keys():
            if self.request.has_key(key) and self.request.get(key) == u'on':
                new_languages.append(all_languages[key])

        # Add languages to the user's preferences.
        for language in Set(new_languages) - Set(old_languages):
            self.user.addLanguage(language)
            self.request.response.addInfoNotification(
                "Added %(language)s to your preferred languages." %
                {'language' : language.englishname})

        # Remove languages from the user's preferences.
        for language in Set(old_languages) - Set(new_languages):
            self.user.removeLanguage(language)
            self.request.response.addInfoNotification(
                "Removed %(language)s from your preferred languages." % 
                {'language' : language.englishname})

        redirection_url = self.request.get('redirection_url')
        if redirection_url:
            self.request.response.redirect(redirection_url)

class RosettaApplicationNavigation(Navigation):

    usedfor = IRosettaApplication

    newlayer = canonical.launchpad.layers.RosettaLayer

    @stepto('groups')
    def groups(self):
        return getUtility(ITranslationGroupSet)

    @stepto('imports')
    def imports(self):
        return getUtility(ITranslationImportQueue)

    @stepto('projects')
    def projects(self):
        # DEPRECATED
        return getUtility(IProjectSet)

    @stepto('products')
    def products(self):
        # DEPRECATED
        return getUtility(IProductSet)
