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
from canonical.launchpad.webapp import Navigation, stepto


class RosettaApplicationView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.languages = helpers.request_languages(self.request)

    @property
    def ubuntu_translationrelease(self):
        release = getUtility(ILaunchpadCelebrities).ubuntu.currentrelease
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


class RosettaPreferencesView:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.error_msg = None
        self.person = getUtility(ILaunchBag).user

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return IRequestPreferredLanguages(self.request).getPreferredLanguages()

    def visible_languages(self):
        class BrowserLanguage:
            def __init__(self, code, englishname, is_checked):
                self.code = code
                self.englishname = englishname

                if is_checked:
                    self.checked = 'checked'
                else:
                    self.checked = ''

        user_languages = list(self.person.languages)

        for language in getUtility(ILanguageSet):
            if language.visible:
                yield BrowserLanguage(
                    code=language.code,
                    englishname=language.englishname,
                    is_checked=language in user_languages)

    def submit(self):
        '''Process a POST request to one of the Rosetta preferences forms.'''

        if (self.request.method == "POST" and
            "SAVE-LANGS" in self.request.form):
            self.submitLanguages()

    def submitLanguages(self):
        '''Process a POST request to the language preference form.

        This list of languages submitted is compared to the the list of
        languages the user has, and the latter is matched to the former.
        '''

        all_languages = getUtility(ILanguageSet)
        old_languages = self.person.languages
        new_languages = []

        for key, value in self.request.form.iteritems():
            if value == u'on':
                try:
                    language = all_languages[key]
                except KeyError:
                    pass
                else:
                    new_languages.append(language)

        # Add languages to the user's preferences.

        for language in Set(new_languages) - Set(old_languages):
            self.person.addLanguage(language)

        # Remove languages from the user's preferences.

        for language in Set(old_languages) - Set(new_languages):
            self.person.removeLanguage(language)


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
