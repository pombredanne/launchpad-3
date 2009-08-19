# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database and utility classes for ITranslatableMessage."""

__metaclass__ = type

__all__ = [
    'TranslatableMessage',
    ]

from zope.interface import implements

from lp.translations.interfaces.translatablemessage import (
    ITranslatableMessage)


class TranslatableMessage(object):
    """See `ITranslatableMessage`."""
    implements(ITranslatableMessage)

    potmsgset = None
    pofile = None
    sequence = 0

    def __init__(self, potmsgset, pofile):
        assert (pofile.potemplate.getPOTMsgSetByID(potmsgset.id) != None,
          "POTMsgSet and POFile must refer to the same POTemplate.")

        self.potmsgset = potmsgset
        self.pofile = pofile
        self.sequence = potmsgset.getSequence(self.potemplate)
        self.potemplate = pofile.potemplate
        self.language = pofile.language
        self.variant = pofile.variant

        self._current_translation = self.potmsgset.getCurrentTranslationMessage(
            self.language, self.potemplate, self.variant)

    def isObsolete(self):
        """See 'ITranslatableMessage'"""
        return self.getSequenceNumber() == 0

    def isCurrentDiverged(self):
        """See 'ITranslatableMessage'"""
        return self._current_translation.potemplate == self.potemplate

    def isCurrentEmpty(self):
        """See 'ITranslatableMessage'"""
        return self._current_translation.is_empty

    def isCurrentImported(self):
        """See 'ITranslatableMessage'"""
        return self._current_translation.is_imported

    def getCurrentTranslation(self):
        """See 'ITranslatableMessage'"""
        return self._current_translation

    def getImportedTranslation(self):
        """See 'ITranslatableMessage'"""
        return self.potmsgset.getImportedTranslationMessage(self.language,
                                                            self.potemplate,
                                                            self.variant)

    def getSharedTranslation(self):
        """See 'ITranslatableMessage'"""
        return self.potmsgset.getSharedTranslationMessage(self.language,
                                                          self.variant)

    def getSuggestions(self, only_new):
        """See 'ITranslatableMessage'"""
        return self.potmsgset.getLocalTranslationMessages(self.potemplate,
                                                          self.language,
                                                          only_new)

    def getExternalTranslations(self):
        """See 'ITranslatableMessage'"""
        lang = self.language
        externally_used = (
            self.potmsgset.getExternallyUsedTranslationMessages(lang))
        externally_suggested = (
            self.potmsgset.getExternallySuggestedTranslationMessages(lang))
        return list(externally_used) + list(externally_suggested)

