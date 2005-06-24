# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['TranslationGroup', 'TranslationGroupSet']

from zope.interface import implements
from zope.exceptions import NotFoundError

from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import CurrencyCol
from sqlobject import MultipleJoin, RelatedJoin
from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import \
    ITranslationGroup, ITranslationGroupSet, IAddFormCustomization

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT

from canonical.launchpad.database.translator import Translator
from canonical.launchpad.database.language import Language

class TranslationGroup(SQLBase):
    """A TranslationGroup."""

    implements(ITranslationGroup)

    # default to listing alphabetically
    _defaultOrder = 'name'

    # db field names
    name = StringCol(unique=True, alternateID=True, notNull=True)
    title = StringCol(notNull=True)
    summary = StringCol(notNull=True)
    datecreated = DateTimeCol(notNull=True, default=DEFAULT)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    # useful joins
    products = MultipleJoin('Product', joinColumn='translationgroup')
    projects = MultipleJoin('Project', joinColumn='translationgroup')
    distributions = MultipleJoin('Distribution', joinColumn='translationgroup')
    languages = RelatedJoin('Language', joinColumn='translationgroup',
        intermediateTable='Translator', otherColumn='language')
    translators = MultipleJoin('Translator', joinColumn='translationgroup')

    # used to note additions
    def add(self, content):
        """See ITranslationGroup."""
        return content

    # adding and removing translators
    def remove_translator(self, translator):
        """See ITranslationGroup."""
        Translator.delete(translator.id)

    # get a translator by language or code
    def query_translator(self, language):
        """See ITranslationGroup."""
        return Translator.selectOneBy(languageID=language.id,
            translationgroupID=self.id)

    # get a translator by code
    def __getitem__(self, code):
        """See ITranslationGroup."""
        language = Language.byCode(code)
        result = Translator.selectOneBy(languageID=language.id,
            translationgroupID=self.id)
        if result is None:
            raise NotFoundError, code
        return result


class TranslationGroupSet:

    implements(ITranslationGroupSet)

    title = 'Rosetta Translation Groups'

    def __iter__(self):
        """See ITranslationGroupSet."""
        for group in TranslationGroup.select():
            yield group

    def __getitem__(self, name):
        """See ITranslationGroupSet."""
        try:
            return TranslationGroup.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError, name

    def new(self, name, title, summary, owner):
        """See ITranslationGroupSet."""
        return TranslationGroup(
            name=name,
            title=title,
            summary=summary,
            owner=owner)

