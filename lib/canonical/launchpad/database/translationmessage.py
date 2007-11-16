# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'TranslationMessage',
    'DummyTranslationMessage',
    'TranslationMessageSet'
    ]

from datetime import datetime
import pytz

from zope.interface import implements
from sqlobject import BoolCol, ForeignKey, SQLObjectNotFound, StringCol

from canonical.cachedproperty import cachedproperty
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    ITranslationMessage, ITranslationMessageSet, RosettaTranslationOrigin,
    TranslationValidationStatus)


class TranslationMessageMixIn:
    """This class is not designed to be used directly.

    You should inherite from it and implement full ITranslationMessage
    interface to use the methods and properties defined here.
    """

    @cachedproperty
    def plural_forms(self):
        """See `ITranslationMessage`."""
        if self.potmsgset.msgid_plural is None:
            # This message is a singular message.
            return 1
        elif self.pofile.language.pluralforms is None:
            # It's a plural form, but we don't know plural forms for this
            # message. Fallback to '2'.
            return 2
        else:
            # It's a plural form, and we know it's number of entries for this
            # language.
            return self.pofile.language.pluralforms

    def makeHTMLID(self, suffix=None):
        """See `ITranslationMessage`."""
        elements = [self.pofile.language.code]
        if suffix is not None:
            elements.append(suffix)
        return self.potmsgset.makeHTMLID('_'.join(elements))


class DummyTranslationMessage(TranslationMessageMixIn):
    """Represents an `ITranslationMessage` where we don't yet HAVE it.

    We do not put TranslationMessages in the database when we only have
    default information. We can represent them from the existing data and
    logic.
    """
    implements(ITranslationMessage)

    def __init__(self, pofile, potmsgset):
        # Check whether we already have a suitable TranslationMessage, in
        # which case, the dummy one must not be used.
        assert potmsgset.getCurrentTranslationMessage(
            pofile.language) is None, (
                'This translation message already exists in the database.')

        self.id = None
        self.pofile = pofile
        self.potmsgset = potmsgset
        UTC = pytz.timezone('UTC')
        self.date_created = datetime.now(UTC)
        self.submitter = None
        self.date_reviewed = None
        self.reviewer = None
        self.msgstr0 = None
        self.msgstr1 = None
        self.msgstr2 = None
        self.msgstr3 = None
        self.comment = None
        self.origin = RosettaTranslationOrigin.ROSETTAWEB
        self.validation_status = TranslationValidationStatus.UNKNOWN
        self.is_current = True
        self.is_complete = False
        self.is_fuzzy = False
        self.is_imported = False
        self.is_empty = True
        self.was_obsolete_in_last_import = False
        self.was_complete_in_last_import = False
        self.was_fuzzy_in_last_import = False
        if self.potmsgset.msgid_plural is None:
            self.translations = [None]
        else:
            self.translations = [None] * self.plural_forms

    def destroySelf(self):
        """See `ITranslationMessage`."""
        # This object is already non persistent, so nothing needs to be done.
        return


class TranslationMessage(SQLBase, TranslationMessageMixIn):
    implements(ITranslationMessage)

    _table = 'TranslationMessage'

    pofile = ForeignKey(foreignKey='POFile', dbName='pofile', notNull=True)
    potmsgset = ForeignKey(
        foreignKey='POTMsgSet', dbName='potmsgset', notNull=True)
    date_created = UtcDateTimeCol(
        dbName='date_created', notNull=True, default=UTC_NOW)
    submitter = ForeignKey(
        foreignKey='Person', dbName='submitter', notNull=True)
    date_reviewed = UtcDateTimeCol(
        dbName='date_reviewed', notNull=False, default=None)
    reviewer = ForeignKey(
        foreignKey='Person', dbName='reviewer', notNull=False, default=None)
    msgstr0 = ForeignKey(
        foreignKey='POTranslation', dbName='msgstr0', notNull=True)
    msgstr1 = ForeignKey(
        foreignKey='POTranslation', dbName='msgstr1', notNull=True)
    msgstr2 = ForeignKey(
        foreignKey='POTranslation', dbName='msgstr2', notNull=True)
    msgstr3 = ForeignKey(
        foreignKey='POTranslation', dbName='msgstr3', notNull=True)
    comment = StringCol(
        dbName='comment', notNull=False, default=None)
    origin = EnumCol(
        dbName='origin', notNull=True, schema=RosettaTranslationOrigin)
    validation_status = EnumCol(
        dbName='validation_status', notNull=True,
        schema=TranslationValidationStatus)
    is_current = BoolCol(dbName='is_current', notNull=True, default=False)
    is_fuzzy = BoolCol(dbName='is_fuzzy', notNull=True, default=False)
    is_imported = BoolCol(dbName='is_imported', notNull=True, default=False)
    was_obsolete_in_last_import = BoolCol(
        dbName='was_obsolete_in_last_import', notNull=True, default=False)
    was_fuzzy_in_last_import = BoolCol(
        dbName='was_fuzzy_in_last_import', notNull=True, default=False)

    def _set_is_current(self, value):
        """Unset current message before setting this as current.

        :param value: Whether we want this translation message as the new
            current one.

        If there is already another current message, we unset it first.
        """
        assert value is not None, 'is_current field cannot be None.'

        if value and not self.is_current:
            # We are setting this message as the current one. We need to
            # change current one to non current before.
            current_translation_message = (
                self.potmsgset.getCurrentTranslationMessage(
                    self.pofile.language))
            if current_translation_message is not None:
                current_translation_message.is_current = False
                # We need this syncUpdate so the old current one change is
                # stored first in the database. This is because we can only
                # have a TranslationMessage with the is_current flag set
                # to TRUE.
                current_translation_message.syncUpdate()

        self._SO_set_is_current(value)

    def _set_is_imported(self, value):
        """Unset current imported message before setting this as imported.

        :param value: Whether we want this translation message as the new
            imported one.

        If there is already another imported message, we unset it first.
        """
        assert value is not None, 'is_imported field cannot be None.'

        if value and not self.is_imported:
            # We are setting this message as the current one. We need to
            # change current one to non current before.
            imported_translation_message = (
                self.potmsgset.getImportedTranslationMessage(
                    self.pofile.language))
            if imported_translation_message is not None:
                imported_translation_message.is_imported = False
                # We need this syncUpdate so the old imported one change is
                # stored first in the database. This is because we can only
                # have a TranslationMessage with the is_imported flag set
                # to TRUE.
                imported_translation_message.syncUpdate()

        self._SO_set_is_imported(value)

    def _get_was_obsolete_in_last_import(self):
        """Override getter for was_obsolete_in_last_import.

        When the message is not imported makes no sense to use this flag.
        """
        assert self.is_imported, 'The message is not imported.'

        return self._SO_get_was_obsolete_in_last_import()

    def _get_was_fuzzy_in_last_import(self):
        """Override getter for was_fuzzy_in_last_import.

        When the message is not imported makes no sense to use this flag.
        """
        assert self.is_imported, 'The message is not imported.'

        return self._SO_get_was_fuzzy_in_last_import()

    @cachedproperty
    def translations(self):
        """See `ITranslationMessage`."""
        msgstrs = [self.msgstr0, self.msgstr1, self.msgstr2, self.msgstr3]
        translations = []
        # Return translations for no more plural forms than the POFile knows.
        for msgstr in msgstrs[:self.plural_forms]:
            if msgstr is None:
                translations.append(None)
            else:
                translations.append(msgstr.translation)
        return translations

    @cachedproperty
    def is_complete(self):
        """See `ITranslationMessage`."""
        if self.msgstr0 is None:
            # No translation for default form (plural form zero).  Incomplete.
            return False
        if self.potmsgset.msgid_plural is None:
            # No plural form needed.  Form zero is enough.
            return True
        return None not in self.translations

    @property
    def is_empty(self):
        """See `ITranslationMessage`."""
        for translation in self.translations:
            if translation is not None:
                # There is at least one translation.
                return False
        # We found no translations in this translation_message
        return True


class TranslationMessageSet:
    """See `ITranslationMessageSet`."""
    implements(ITranslationMessageSet)

    def getByID(self, ID):
        """See `ILanguageSet`."""
        try:
            return TranslationMessage.get(ID)
        except SQLObjectNotFound:
            return None
