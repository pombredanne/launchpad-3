# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.launchpad.interfaces import ITranslator
from canonical.launchpad.webapp import (
    LaunchpadEditFormView, LaunchpadView, action, canonical_url)

__all__ = [
    'TranslatorEditView',
    'TranslatorRemoveView'
    ]

class TranslatorEditView(LaunchpadEditFormView):
    """View class to edit ITranslationGroup objects"""

    schema = ITranslator
    field_names = ['language', 'translator']

    @action("Change")
    def change_action(self, action, data):
        """Edit the translator that does translations for a given language."""
        self.updateContextFromData(data)

    def validate(self, data):
        """Don't allow to change the language if it's already in the group."""
        language = data.get('language')
        translation_group = self.context.translationgroup
        if (self.context.language != language and
            translation_group.query_translator(language) is not None):
            # The language changed but it already exists so we cannot accept
            # this edit.
            self.setFieldError('language',
                "There is already a translator for this language")

    @property
    def next_url(self):
        return canonical_url(self.context.translationgroup)


class TranslatorRemoveView(LaunchpadView):

    def initialize(self):
        if self.request.method == 'POST':
            self.translationgroup = self.context.translationgroup
            if 'remove' in self.request.form:
                self.remove()
            self.request.response.redirect(
                canonical_url(self.translationgroup))

    def remove(self):
        """Remove the ITranslator from the associated ITranslationGroup."""
        self.translationgroup.remove_translator(self.context)
        self.request.response.addInfoNotification(
            'Removed %s as the %s translator for %s.' % (
                self.context.translator.displayname,
                self.context.language.englishname,
                self.translationgroup.title))
