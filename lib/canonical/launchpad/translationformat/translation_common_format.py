# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TranslationMessage',
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import ITranslationMessage


class TranslationMessage:
    """See `ITranslationMessage`."""
    implements(ITranslationMessage)

    def __init__(self):
        self.msgid = None
        self.msgid_plural = None
        self._translations = []
        self.comment = None
        self.source_comment = None
        self.file_references = None
        self.flags = set()
        self.obsolete = False
        self.nplurals = None
        self.pluralExpr = None

    @property
    def translations(self):
        """See `ITranslationMessage`."""
        return self._translations

    def addTranslation(self, plural_form, translation):
        """See `ITranslationMessage`."""
        # Unlike msgids, we can't assume that groups of translations are
        # contiguous. I.e. we might get translations for plural forms 0 and 2,
        # but not 1. This means we need to add empty values if plural_form >
        # len(self._translations).
        #
        # We raise an error if plural_form < len(self.translations).
        assert plural_form >= len(self._translations), (
            'This message already has a translation for plural form %d' % (
                plural_form))

        if plural_form > len(self.translations):
            # There is a hole in the list of translations so we fill it with
            # None.
            self._translations.extend(
                [None] * (plural_form - len(self._translations)))

        self._translations.append(translation)

    def flagsText(self, flags=None):
        """See `ITranslationMessage`."""
        if flags is not None:
            return flags

        return u''
