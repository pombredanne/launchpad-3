# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Browser code for translation groups."""

__metaclass__ = type
__all__ = [
    'TranslationGroupAddTranslatorView',
    'TranslationGroupAddView',
    'TranslationGroupEditView',
    'TranslationGroupNavigation',
    'TranslationGroupReassignmentView',
    'TranslationGroupSetNavigation',
    'TranslationGroupView',
    ]

import operator

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ITranslationGroup, ITranslationGroupSet, ITranslator, ITranslatorSet,
    NotFoundError
    )
from canonical.launchpad.browser.objectreassignment import (
    ObjectReassignmentView)
from canonical.launchpad.webapp import (
    action, canonical_url, GetitemNavigation, LaunchpadEditFormView,
    LaunchpadFormView
    )


class TranslationGroupNavigation(GetitemNavigation):

    usedfor = ITranslationGroup


class TranslationGroupSetNavigation(GetitemNavigation):

    usedfor = ITranslationGroupSet


class TranslationGroupView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.translation_groups = getUtility(ITranslationGroupSet)

    @property
    def translator_list(self):
        result = []
        for item in self.context.translators:
            result.append({'lang': item.language.englishname,
                           'person': item.translator,
                           'code': item.language.code,
                           'datecreated': item.datecreated})
        result.sort(key=operator.itemgetter('lang'))
        return result


class TranslationGroupAddTranslatorView(LaunchpadFormView):
    """View class for the "appoint a translator" page"""

    schema = ITranslator
    field_names = ['language', 'translator']

    @action("Add", name="add")
    def add_action(self, action, data):
        """Appoint a translator to do translations for given language.

        Create a translator who, within this group, will be responsible for
        the selected language.  Within a translation group, a language can
        have at most one translator.  Of course the translator may be either a
        person or a group, however.
        """
        language = data.get('language')
        translator = data.get('translator')
        getUtility(ITranslatorSet).new(self.context, language, translator)

    def validate(self, data):
        """Do not allow new translators for already existing languages."""
        language = data.get('language')
        if self.context.query_translator(language):
            self.setFieldError('language',
                "There is already a translator for this language")

    @property
    def next_url(self):
        return canonical_url(self.context)


class TranslationGroupEditView(LaunchpadEditFormView):
    """View class to edit ITranslationGroup details."""

    schema = ITranslationGroup
    field_names = ['name', 'title', 'summary']

    @action("Change")
    def change_action(self, action, data):
        """Edit ITranslationGroup details."""
        self.updateContextFromData(data)

    def validate(self, data):
        """Check that we follow fields restrictions."""
        new_name = data.get('name')
        translation_group = getUtility(ITranslationGroupSet)
        if (self.context.name != new_name):
            try:
                translation_group[new_name]
            except NotFoundError:
                # The new name doesn't exist so it's valid.
                return
            self.setFieldError('name',
                "There is already a translation group with this name")

    @property
    def next_url(self):
        return canonical_url(self.context)


class TranslationGroupAddView(LaunchpadFormView):
    """View class to add ITranslationGroup objects."""

    schema = ITranslationGroup
    field_names = ['name', 'title', 'summary']

    @action("Add", name="add")
    def add_action(self, action, data):
        """Add a new translation group to Launchpad."""
        name = data.get('name')
        title = data.get('title')
        summary = data.get('summary')
        new_group = getUtility(ITranslationGroupSet).new(
            name=name, title=title, summary=summary, owner=self.user)

        self.next_url = canonical_url(new_group)

    def validate(self, data):
        """Do not allow new groups with duplicated names."""
        name = data.get('name')
        try:
            self.context[name]
        except NotFoundError:
            # The given name doesn't exist so it's valid.
            return
        self.setFieldError('name',
            "There is already a translation group with such name")


class TranslationGroupReassignmentView(ObjectReassignmentView):
    """View class for changing translation group owner."""

    @property
    def contextName(self):
        return self.context.title or self.context.name

    @property
    def next_url(self):
        return canonical_url(self.context)
