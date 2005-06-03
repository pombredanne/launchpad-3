# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.launchpad.interfaces import ILanguageSet, ILaunchBag, IGeoIP, \
    IRequestPreferredLanguages
from canonical.launchpad import helpers


class RosettaApplicationView(object):

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
        ip = self.request.get('HTTP_X_FORWARDED_FOR', None)
        if ip is None:
            ip = self.request.get('REMOTE_ADDR', None)
        if ip is None:
            return None
        gi = getUtility(IGeoIP)
        return gi.country_by_addr(ip)

    def browserLanguages(self):
        return IRequestPreferredLanguages(self.request).getPreferredLanguages()


class ViewPreferences:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.error_msg = None
        self.person = getUtility(ILaunchBag).user

    def languages(self):
        return [
            language
            for language in getUtility(ILanguageSet)
            if language.visible
            ]

    def selectedLanguages(self):
        return self.person.languages

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

        old_languages = self.person.languages

        if 'selectedlanguages' in self.request.form:
            if isinstance(self.request.form['selectedlanguages'], list):
                new_languages = self.request.form['selectedlanguages']
            else:
                new_languages = [self.request.form['selectedlanguages']]
        else:
            new_languages = []

        # XXX
        # Making the values submitted in the form be the language codes rather
        # than the English names would make this simpler. However, given that
        # the language preferences form is currently based on JavaScript, it
        # would take JavaScript hacking to make that work.
        #
        # https://launchpad.ubuntu.com/malone/bugs/127
        # -- Dafydd, 2005/02/03

        # Add languages.
        for englishname in new_languages:
            for language in self.languages():
                if language.englishname == englishname:
                    if language not in old_languages:
                        self.person.addLanguage(language)

        # Remove languages.
        for language in old_languages:
            if language.englishname not in new_languages:
                self.person.removeLanguage(language)

