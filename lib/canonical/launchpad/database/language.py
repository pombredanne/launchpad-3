# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey, StringCol, IntCol, MultipleJoin
from sqlobject import RelatedJoin, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase, quote

# canonical imports
from canonical.launchpad.interfaces.language import ILanguageSet, ILanguage

class LanguageSet(object):
    implements(ILanguageSet)

    def __iter__(self):
        return iter(Language.select(orderBy='englishName'))

    def __getitem__(self, code):
        try:
            return Language.byCode(code)
        except SQLObjectNotFound:
            raise KeyError, code

    def keys(self):
        return [language.code for language in Language.select()]


class Language(SQLBase):
    implements(ILanguage)

    _table = 'Language'

    _columns = [
        StringCol(name='code', dbName='code', notNull=True, unique=True,
            alternateID=True),
        StringCol(name='nativeName', dbName='nativename'),
        StringCol(name='englishName', dbName='englishname'),
        IntCol(name='pluralForms', dbName='pluralforms'),
        StringCol(name='pluralExpression', dbName='pluralexpression'),
    ]

    def translateLabel(self):
        try:
            schema = Schema.byName('translation-languages')
        except SQLObjectNotFound:
            raise RuntimeError("Launchpad installation is broken, " + \
                    "the DB is missing essential data.")
        return Label.selectBy(schemaID=schema.id, name=self.code)

    def translators(self):
        return self.translateLabel().persons()

