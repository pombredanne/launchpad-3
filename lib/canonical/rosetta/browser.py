# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

from sets import Set

from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.launchpad.interfaces import (
    ILanguageSet, ILaunchBag, IGeoIP, IRequestPreferredLanguages, ICountry
    )
from canonical.launchpad import helpers


class RosettaApplicationView:

    translationGroupsPortlet = ViewPageTemplateFile(
            '../launchpad/templates/portlet-rosetta-groups.pt')

    prefLangPortlet = ViewPageTemplateFile(
            '../launchpad/templates/portlet-pref-langs.pt')

    countryPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-country-langs.pt')

    browserLangPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-browser-langs.pt')

    statsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-rosetta-stats.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.languages = helpers.request_languages(self.request)

    def requestCountry(self):
        return ICountry(self.request, None)

    def browserLanguages(self):
        return IRequestPreferredLanguages(self.request).getPreferredLanguages()


class ViewPreferences:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.error_msg = None
        self.person = getUtility(ILaunchBag).user

    def languages(self):
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

