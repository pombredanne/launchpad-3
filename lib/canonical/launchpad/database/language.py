# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Language', 'LanguageSet']

from zope.interface import implements

from sqlobject import StringCol, IntCol, BoolCol
from sqlobject import RelatedJoin, SQLObjectNotFound
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import ILanguageSet, ILanguage


class Language(SQLBase):
    implements(ILanguage)

    _table = 'Language'

    code = StringCol(dbName='code', notNull=True, unique=True,
            alternateID=True)
    nativename = StringCol(dbName='nativename')
    englishname = StringCol(dbName='englishname')
    pluralforms = IntCol(dbName='pluralforms')
    pluralexpression = StringCol(dbName='pluralexpression')
    visible = BoolCol(dbName='visible')

    translators = RelatedJoin('Person', joinColumn='language',
        otherColumn='person', intermediateTable='PersonLanguage')

    countries = RelatedJoin('Country', joinColumn='language',
        otherColumn='country', intermediateTable='SpokenIn')


class LanguageSet:
    implements(ILanguageSet)

    def __iter__(self):
        return iter(Language.select(orderBy='englishname'))

    def __getitem__(self, code):
        try:
            return Language.byCode(code)
        except SQLObjectNotFound:
            raise KeyError, code

    def keys(self):
        return [language.code for language in Language.select()]

