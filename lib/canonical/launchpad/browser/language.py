# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Browser code for Language table."""

__metaclass__ = type
__all__ = [
    'LanguageAddView',
    'LanguageContextMenu',
    'LanguageAdminView',
    'LanguageNavigation',
    'LanguageSetContextMenu',
    'LanguageSetNavigation',
    'LanguageSetView',
    'LanguageView',
    ]

import operator

from zope.app.event.objectevent import ObjectCreatedEvent
from zope.component import getUtility
from zope.event import notify

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.browser.launchpad import RosettaContextMenu
from canonical.launchpad.interfaces import (
    ILanguageSet, ILanguage, NotFoundError)
from canonical.launchpad.webapp import (
    GetitemNavigation, LaunchpadView, LaunchpadFormView,
    LaunchpadEditFormView, action, canonical_url)


class LanguageNavigation(GetitemNavigation):
    usedfor = ILanguage

    def traverse(self, name):
        raise NotFoundError


class LanguageSetNavigation(GetitemNavigation):
    usedfor = ILanguageSet


class LanguageSetContextMenu(RosettaContextMenu):
    usedfor = ILanguageSet


class LanguageContextMenu(RosettaContextMenu):
    usedfor = ILanguage


class LanguageSetView:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        form = self.request.form
        self.text = form.get('text')
        self.searchrequested = self.text is not None

    @cachedproperty
    def search_results(self):
        return self.context.search(text=self.text)

    @cachedproperty
    def search_matches(self):
        if self.search_results is not None:
            return self.search_results.count()
        else:
            return 0


class LanguageAddView(LaunchpadFormView):

    schema = ILanguage
    field_names = ['code', 'englishname', 'nativename', 'pluralforms',
                   'pluralexpression', 'visible', 'direction']
    label = 'Register a language in Launchpad'
    language = None

    @action('Add', name='add')
    def add_action(self, action, data):
        """Create the new Language from the form details."""
        self.language = getUtility(ILanguageSet).createLanguage(
            code=data['code'],
            englishname=data['englishname'],
            nativename=data['nativename'],
            pluralforms=data['pluralforms'],
            pluralexpression=data['pluralexpression'],
            visible=data['visible'],
            direction=data['direction'])
        notify(ObjectCreatedEvent(self.language))

    @property
    def next_url(self):
        assert self.language is not None, 'No language has been created'
        return canonical_url(self.language)

    def validate(self, data):
        new_code = data.get('code')
        language_set = getUtility(ILanguageSet)
        if language_set.getLanguageByCode(new_code) is not None:
            self.setFieldError(
                'code', 'There is already a language with that code.')


class LanguageView(LaunchpadView):

    @cachedproperty
    def language_name(self):
        if self.context.nativename is None:
            return self.context.englishname
        else:
            return self.context.nativename

    def translation_teams(self):
        foo = []
        for translation_team in self.context.translation_teams:
            foo.append({
                'expert': translation_team,
                'groups': translation_team.translation_groups,
                })
        return foo

    def getTopContributors(self):
        return self.context.translators[:20]


class LanguageAdminView(LaunchpadEditFormView):
    """Handle an admin form submission."""
    schema = ILanguage

    field_names = ['code', 'englishname', 'nativename', 'pluralforms',
                   'pluralexpression', 'visible', 'direction']

    @action("Admin Language", name="admin")
    def admin_action(self, action, data):
        self.updateContextFromData(data)

