# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['Translator', 'TranslatorSet']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.launchpad.interfaces import \
    ITranslator, ITranslatorSet

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol

class Translator(SQLBase):
    """A Translator in a TranslationGroup."""

    implements(ITranslator)

    # default to listing newest first
    _defaultOrder = '-id'

    # db field names
    translationgroup = ForeignKey(dbName='translationgroup',
        foreignKey='TranslationGroup', notNull=True)
    language = ForeignKey(dbName='language',
        foreignKey='Language', notNull=True)
    translator = ForeignKey(dbName='translator', foreignKey='Person',
        notNull=True)
    datecreated = UtcDateTimeCol(notNull=True, default=DEFAULT)


class TranslatorSet:
    implements(ITranslatorSet)

    def new(self, translationgroup, language, translator):
        return Translator(
            translationgroup=translationgroup,
            language=language,
            translator=translator)

