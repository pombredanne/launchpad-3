# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation for `ITranslatableMessage`."""

__metaclass__ = type

__all__ = [
    'TranslatableMessage',
    ]

from zope.interface import implements

from lp.translations.interfaces.translatablemessage import (
    ITranslatableMessage,
    )


class TranslatableMessage(object):
    """See `ITranslatableMessage`."""
    implements(ITranslatableMessage)

    potmsgset = None
    pofile = None
    sequence = 0

    def __init__(self, potmsgset, pofile):
        """Create a new TranslatableMessage object.

        :param potmsgset: The `IPOTMsgSet` instance that this object refers
          to.
        :param pofile: The `IPOFile` instance that the potmsgset is used
          with.

        Both potmsgset and pofile must be related, meaning they refer to the
        same `IPOTemplate` instance.
        """
        assert pofile.potemplate.getPOTMsgSetByID(potmsgset.id) != None, (
          "POTMsgSet and POFile must refer to the same POTemplate.")

        self.potmsgset = potmsgset
        self.pofile = pofile
        self.sequence = potmsgset.getSequence(pofile.potemplate)
        self.potemplate = pofile.potemplate
        self.language = pofile.language

        self._current_translation = self.potmsgset.getCurrentTranslation(
            self.potemplate, self.language, self.potemplate.translation_side)

    @property
    def is_obsolete(self):
        """See `ITranslatableMessage`"""
        return self.sequence == 0

    @property
    def is_untranslated(self):
        """See `ITranslatableMessage`"""
        if self._current_translation is None:
            return True
        return self._current_translation.is_empty

    @property
    def is_current_diverged(self):
        """See `ITranslatableMessage`"""
        if self._current_translation is None:
            return False
        return self._current_translation.potemplate == self.potemplate

    @property
    def is_current_imported(self):
        """See `ITranslatableMessage`"""
        if self._current_translation is None:
            return False
        return self._current_translation.is_current_upstream

    @property
    def has_plural_forms(self):
        """See `ITranslatableMessage`"""
        return self.potmsgset.msgid_plural is not None

    @property
    def number_of_plural_forms(self):
        """See `ITranslatableMessage`"""
        if self.has_plural_forms:
            return self.pofile.plural_forms
        else:
            return 1

    def getCurrentTranslation(self):
        """See `ITranslatableMessage`"""
        return self._current_translation

    def getImportedTranslation(self):
        """See `ITranslatableMessage`"""
        return self.potmsgset.getOtherTranslation(
            self.language, self.potemplate.translation_side)

    def getSharedTranslation(self):
        """See `ITranslatableMessage`"""
        return self.potmsgset.getSharedTranslation(
            self.language, self.potemplate.translation_side)

    def getAllSuggestions(self):
        """See `ITranslatableMessage`"""
        return self.potmsgset.getLocalTranslationMessages(
            self.potemplate, self.language,
            include_dismissed=True, include_unreviewed=True)

    def getUnreviewedSuggestions(self):
        """See `ITranslatableMessage`"""
        return self.potmsgset.getLocalTranslationMessages(
            self.potemplate, self.language,
            include_dismissed=False, include_unreviewed=True)

    def getDismissedSuggestions(self):
        """See `ITranslatableMessage`"""
        return self.potmsgset.getLocalTranslationMessages(
            self.potemplate, self.language,
            include_dismissed=True, include_unreviewed=False)

    def getExternalTranslations(self):
        """See `ITranslatableMessage`"""
        lang = self.language
        return self.potmsgset.getExternallyUsedTranslationMessages(lang)

    def getExternalSuggestions(self):
        """See `ITranslatableMessage`"""
        lang = self.language
        return self.potmsgset.getExternallySuggestedTranslationMessages(lang)

    def dismissAllSuggestions(self, reviewer, lock_timestamp):
        """See `ITranslatableMessage`"""
        self.potmsgset.dismissAllSuggestions(
            self.pofile, reviewer, lock_timestamp)
