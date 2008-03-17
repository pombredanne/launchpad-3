# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'DummyTranslationMessage',
    'make_plurals_sql_fragment',
    'make_plurals_fragment',
    'TranslationMessage',
    'TranslationMessageSet'
    ]

from datetime import datetime
import pytz

from zope.interface import implements
from sqlobject import BoolCol, ForeignKey, SQLObjectNotFound, StringCol

from canonical.cachedproperty import cachedproperty
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    ITranslationMessage, ITranslationMessageSet, RosettaTranslationOrigin,
    TranslationConstants, TranslationValidationStatus)
from canonical.launchpad.validators.person import public_person_validator


def make_plurals_fragment(fragment, separator):
    """Repeat text fragment for each plural form, separated by separator.

    Inside fragment, use "%(form)d" to represent the applicable plural
    form number.
    """
    return separator.join([
        fragment % {'form': form}
        for form in xrange(TranslationConstants.MAX_PLURAL_FORMS)])


def make_plurals_sql_fragment(fragment, separator="AND"):
    """Compose SQL fragment consisting of clauses for each plural form.

    Creates fragments like "msgstr0 IS NOT NULL AND msgstr1 IS NOT NULL" etc.

    :param fragment: a piece of SQL text to repeat for each msgstr*, using
        "%(form)d" to represent the number of each form: "msgstr%(form)d IS
        NOT NULL".  Parentheses are added.
    :param separator: string to insert between the repeated clauses, e.g.
        "AND" (default) or "OR".  Spaces are added.
    """
    return make_plurals_fragment("(%s)" % fragment, " %s " % separator)


class TranslationMessageMixIn:
    """This class is not designed to be used directly.

    You should inherit from it and implement the full `ITranslationMessage`
    interface to use the methods and properties defined here.
    """

    @cachedproperty
    def plural_forms(self):
        """See `ITranslationMessage`."""
        if self.potmsgset.msgid_plural is None:
            # This message is a singular message.
            return 1
        else:
            return self.pofile.plural_forms

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

        for form in xrange(TranslationConstants.MAX_PLURAL_FORMS):
            setattr(self, 'msgstr%d' % form, None)

        self.comment = None
        self.origin = RosettaTranslationOrigin.ROSETTAWEB
        self.validation_status = TranslationValidationStatus.UNKNOWN
        self.is_current = True
        self.is_complete = False
        self.is_fuzzy = False
        self.is_imported = False
        self.is_empty = True
        self.is_hidden = True
        self.was_obsolete_in_last_import = False
        self.was_complete_in_last_import = False
        self.was_fuzzy_in_last_import = False
        if self.potmsgset.msgid_plural is None:
            self.translations = [None]
        else:
            self.translations = [None] * self.plural_forms

    @property
    def all_msgstrs(self):
        """See `ITranslationMessage`."""
        return [None] * TranslationConstants.MAX_PLURAL_FORMS

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
        foreignKey='Person',
        validator=public_person_validator, dbName='submitter', notNull=True)
    date_reviewed = UtcDateTimeCol(
        dbName='date_reviewed', notNull=False, default=None)
    reviewer = ForeignKey(
        dbName='reviewer', foreignKey='Person',
        validator=public_person_validator, notNull=False, default=None)

    assert TranslationConstants.MAX_PLURAL_FORMS == 6, (
        "Change this code to support %d plural forms."
        % TranslationConstants.MAX_PLURAL_FORMS)
    msgstr0 = ForeignKey(foreignKey='POTranslation', dbName='msgstr0',
                         notNull=False, default=DEFAULT)
    msgstr1 = ForeignKey(foreignKey='POTranslation', dbName='msgstr1',
                         notNull=False, default=DEFAULT)
    msgstr2 = ForeignKey(foreignKey='POTranslation', dbName='msgstr2',
                         notNull=False, default=DEFAULT)
    msgstr3 = ForeignKey(foreignKey='POTranslation', dbName='msgstr3',
                         notNull=False, default=DEFAULT)
    msgstr4 = ForeignKey(foreignKey='POTranslation', dbName='msgstr4',
                         notNull=False, default=DEFAULT)
    msgstr5 = ForeignKey(foreignKey='POTranslation', dbName='msgstr5',
                         notNull=False, default=DEFAULT)

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
                    self.pofile.language, self.pofile.variant))
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
                    self.pofile.language, self.pofile.variant))
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
    def all_msgstrs(self):
        """See `ITranslationMessage`."""
        return [
            getattr(self, 'msgstr%d' % form)
            for form in xrange(TranslationConstants.MAX_PLURAL_FORMS)]

    @cachedproperty
    def translations(self):
        """See `ITranslationMessage`."""
        msgstrs = self.all_msgstrs
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

    @property
    def is_hidden(self):
        """See `ITranslationMessage`."""
        # If this message is currently used or has been imported,
        # it's not hidden.
        if self.is_current or self.is_imported:
            return False

        # Otherwise, if this suggestions has been reviewed and
        # rejected (i.e. current translation's date_reviewed is
        # more recent than the date of suggestion's date_created),
        # it is hidden.
        # If it has not been reviewed yet, it's not hidden.
        current = self.potmsgset.getCurrentTranslationMessage(
            self.pofile.language, self.pofile.variant)
        # If there is no current translation, none of the
        # suggestions have been reviewed, so they are all shown.
        if current is None:
            return False
        date_reviewed = current.date_reviewed
        # For an imported current translation, no date_reviewed is set.
        if date_reviewed is None:
            date_reviewed = current.date_created
        return date_reviewed > self.date_created


class TranslationMessageSet:
    """See `ITranslationMessageSet`."""
    implements(ITranslationMessageSet)

    def getByID(self, ID):
        """See `ILanguageSet`."""
        try:
            return TranslationMessage.get(ID)
        except SQLObjectNotFound:
            return None
