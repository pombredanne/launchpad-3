# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Language', 'LanguageSet']

from zope.interface import implements
from zope.exceptions import NotFoundError

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

    @property
    def displayname(self):
        """See ILanguage."""
        return '%s (%s)' % (self.englishname, self.code)


class LanguageSet:
    implements(ILanguageSet)

    def __iter__(self):
        """See ILanguageSet."""
        return iter(Language.select(orderBy='englishname'))

    def __getitem__(self, code):
        """See ILanguageSet."""

        try:
            return Language.byCode(code)
        except SQLObjectNotFound:
            raise NotFoundError, code

    def keys(self):
        """See ILanguageSet."""
        return [language.code for language in Language.select()]

    def canonicalise_language_code(self, code):
        """See ILanguageSet."""

        if '-' in code:
            language, country = code.split('-', 1)

            return "%s_%s" % (language, country.upper())
        else:
            return code

    def codes_to_languages(self, codes):
        """See ILanguageSet."""

        languages = []

        for code in [self.canonicalise_language_code(code) for code in codes]:
            try:
                languages.append(self[code])
            except KeyError:
                pass

        return languages

