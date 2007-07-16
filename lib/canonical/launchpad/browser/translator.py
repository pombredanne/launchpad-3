# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import cgi

from canonical.launchpad.interfaces import ITranslator
from canonical.launchpad.webapp import (
    LaunchpadEditFormView, LaunchpadFormView, action, canonical_url)

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
        existing_translator = translation_group.query_translator(language)
        if (self.context.language != language and
            existing_translator is not None):
            # The language changed but it already exists so we cannot accept
            # this edit.
            existing_translator_link = '<a href="%s">%s</a>' % (
                canonical_url(existing_translator.translator),
                cgi.escape(existing_translator.translator.displayname))

            self.setFieldError('language',
                '%s is already a translator for this language' % (
                    existing_translator_link))

    @property
    def next_url(self):
        return canonical_url(self.context.translationgroup)


class TranslatorRemoveView(LaunchpadFormView):
    schema = ITranslator
    field_names = []

    @action("Cancel")
    def cancel(self, action, data):
        self.request.response.addInfoNotification(
            'Canceled the request to remove %s as the %s translator for %s.' %
                (self.context.translator.displayname,
                 self.context.language.englishname,
                 self.context.translationgroup.title))

    @action("Remove")
    def remove(self, action, data):
        """Remove the ITranslator from the associated ITranslationGroup."""
        self.context.translationgroup.remove_translator(self.context)
        self.request.response.addInfoNotification(
            'Removed %s as the %s translator for %s.' % (
                self.context.translator.displayname,
                self.context.language.englishname,
                self.context.translationgroup.title))

    @property
    def next_url(self):
        return canonical_url(self.context.translationgroup)
