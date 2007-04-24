# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from canonical.launchpad.interfaces import ITranslator
from canonical.launchpad.webapp import (
    LaunchpadEditFormView, action, canonical_url)

__all__ = [
    'TranslatorEditView'
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
        """Do not allow an edition action to overwrite an existing translator.

        We don't allow a translator to be appointed for a language that
        already has a translator within that group.  If we did, it would be
        too easy accidentally to replace a translator, e.g. by picking the
        wrong language in this form.
        """
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
