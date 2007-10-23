# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Common file format classes shared across all formats."""

__metaclass__ = type

__all__ = [
    'TranslationFile',
    'TranslationMessageData',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationFile, ITranslationMessageData)


class TranslationFile:
    """See `ITranslationFile`."""
    implements(ITranslationFile)

    def __init__(self):
        self.header = None
        self.messages = []
        self.path = None
        self.translation_domain = None
        self.is_template = None
        self.language_code = None


class TranslationMessageData:
    """See `ITranslationMessageData`."""
    implements(ITranslationMessageData)

    def __init__(self):
        self.msgid = None
        self.msgid_plural = None
        self.context = None
        self._translations = []
        self.comment = u''
        self.source_comment = u''
        self.file_references = u''
        self.flags = set()
        self.is_obsolete = False

    @property
    def translations(self):
        """See `ITranslationMessageData`."""
        return self._translations

    def addTranslation(self, plural_form, translation):
        """See `ITranslationMessageData`."""
        # Unlike msgids, we can't assume that groups of translations are
        # contiguous. I.e. we might get translations for plural forms 0 and 2,
        # but not 1. This means we need to add empty values if plural_form >
        # len(self._translations).
        #
        # We raise an error if plural_form < len(self.translations).
        assert plural_form is not None, 'plural_form cannot be None!'
        assert plural_form >= len(self._translations), (
            'This message already has a translation for plural form %d' %
                plural_form)

        if plural_form > len(self.translations):
            # There is a hole in the list of translations so we fill it with
            # None.
            self._translations.extend(
                [None] * (plural_form - len(self._translations)))

        self._translations.append(translation)

    def resetAllTranslations(self):
        """See `ITranslationMessageData`."""
        self._translations = []

