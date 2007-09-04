# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Language', 'LanguageSet']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    StringCol, IntCol, BoolCol, SQLRelatedJoin, SQLObjectNotFound, OR,
    CONTAINSSTRING)

from canonical.database.sqlbase import SQLBase
from canonical.database.enumcol import EnumCol
from canonical.lp.dbschema import TextDirection
from canonical.launchpad.interfaces import (
    ILanguageSet, ILanguage, IPersonSet, NotFoundError)


class Language(SQLBase):
    implements(ILanguage)

    _table = 'Language'

    code = StringCol(
        dbName='code', notNull=True, unique=True, alternateID=True)
    uuid = StringCol(dbName='uuid', notNull=False, default=None)
    nativename = StringCol(dbName='nativename')
    englishname = StringCol(dbName='englishname')
    pluralforms = IntCol(dbName='pluralforms')
    pluralexpression = StringCol(dbName='pluralexpression')
    visible = BoolCol(dbName='visible', notNull=True)
    direction = EnumCol(
        dbName='direction', notNull=True, schema=TextDirection,
        default=TextDirection.LTR)

    translation_teams = SQLRelatedJoin(
        'Person', joinColumn="language",
        intermediateTable='Translator', otherColumn='translator')

    _countries = SQLRelatedJoin(
        'Country', joinColumn='language', otherColumn='country',
        intermediateTable='SpokenIn')

    # Define a read/write property `countries` so it can be passed
    # to language administration `LaunchpadFormView`.
    def _getCountries(self):
        return self._countries

    def _setCountries(self, countries):
        for country in self._countries:
            if country not in countries:
                self.removeCountry(country)
        for country in countries:
            if country not in self._countries:
                self.addCountry(country)
    countries = property(_getCountries, _setCountries)

    @property
    def displayname(self):
        """See ILanguage."""
        return '%s (%s)' % (self.englishname, self.code)

    @property
    def alt_suggestion_language(self):
        """See ILanguage."""
        if self.code in ['pt_BR',]:
            return None
        elif self.code == 'nn':
            return Language.byCode('nb')
        elif self.code == 'nb':
            return Language.byCode('nn')
        codes = self.code.split('_')
        if len(codes) == 2:
            return Language.byCode(codes[0])
        return None

    @property
    def dashedcode(self):
        """See ILanguage."""
        return self.code.replace('_', '-')

    @property
    def abbreviated_text_dir(self):
        """See ILanguage."""
        if self.direction == TextDirection.LTR:
            return 'ltr'
        elif self.direction == TextDirection.RTL:
            return 'rtl'
        else:
            assert False, "unknown text direction"

    @property
    def translators(self):
        """See ILanguage."""
        personset = getUtility(IPersonSet)
        return personset.getTranslatorsByLanguage(self)


class LanguageSet:
    implements(ILanguageSet)

    @property
    def common_languages(self):
        return iter(Language.select(
            'visible IS TRUE',
            orderBy='englishname'))

    def __iter__(self):
        """See ILanguageSet."""
        return iter(Language.select(orderBy='englishname'))

    def __getitem__(self, code):
        """See ILanguageSet."""
        language = self.getLanguageByCode(code)

        if language is None:
            raise NotFoundError, code

        return language

    def getLanguageByCode(self, code):
        """See ILanguageSet."""
        assert isinstance(code, basestring), (
            "%s is not a valid type for 'code'" % type(code))
        try:
            return Language.byCode(code)
        except SQLObjectNotFound:
            return None

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

    def getLanguageAndVariantFromString(self, language_string):
        """See ILanguageSet."""
        if language_string is None:
            return (None, None)

        if u'@' in language_string:
            # Seems like this entry is using a variant entry.
            language_code, language_variant = language_string.split(u'@')
        else:
            language_code = language_string
            language_variant = None

        try:
            language = self[language_code]
        except NotFoundError:
            # We don't have such language in our database so we cannot
            # guess it using this method.
            return (None, None)

        return (language, language_variant)

    def createLanguage(self, code, englishname, nativename=None,
                       pluralforms=None, pluralexpression=None, visible=True,
                       direction=TextDirection.LTR):
        """See ILanguageSet."""
        return Language(
            code=code, englishname=englishname, nativename=nativename,
            pluralforms=pluralforms, pluralexpression=pluralexpression,
            visible=visible, direction=direction)

    def search(self, text):
        """See ILanguageSet."""
        if text:
            text.lower()
            results = Language.select(
                OR (
                    CONTAINSSTRING(Language.q.code, text),
                    CONTAINSSTRING(Language.q.englishname, text)
                    ),
                orderBy='englishname'
                )
        else:
            results = None

        return results
