# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

"""Vocabularies pulling stuff from the database.

You probably don't want to use these classes directly - see the
docstring in __init__.py for details.
"""

__metaclass__ = type

__all__ = [
    'ComponentVocabulary',
    'CountryNameVocabulary',
    'FilteredDeltaLanguagePackVocabulary',
    'FilteredDistroArchSeriesVocabulary',
    'FilteredFullLanguagePackVocabulary',
    'FilteredLanguagePackVocabulary',
    'LanguageVocabulary',
    'PackageReleaseVocabulary',
    'PPAVocabulary',
    'ProcessorFamilyVocabulary',
    'ProcessorVocabulary',
    'TranslatableLanguageVocabulary',
    'TranslationGroupVocabulary',
    'TranslationMessageVocabulary',
    'TranslationTemplateVocabulary',
    ]

from sqlobject import (
    AND,
    SQLObjectNotFound,
    )
from storm.expr import (
    SQL,
    )
from zope.component import getUtility
from zope.interface import implements
from zope.schema.vocabulary import (
    SimpleTerm,
    )

from canonical.database.sqlbase import (
    quote,
    sqlvalues,
    )
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.vocabulary import (
    IHugeVocabulary,
    NamedSQLObjectVocabulary,
    SQLObjectVocabularyBase,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.model.person import Person
from lp.services.worlddata.interfaces.language import ILanguage
from lp.services.worlddata.model.country import Country
from lp.services.worlddata.model.language import Language
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.component import Component
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.model.processor import (
    Processor,
    ProcessorFamily,
    )
from lp.soyuz.model.sourcepackagerelease import SourcePackageRelease
from lp.translations.enums import LanguagePackType
from lp.translations.model.languagepack import LanguagePack
from lp.translations.model.potemplate import POTemplate
from lp.translations.model.translationgroup import TranslationGroup
from lp.translations.model.translationmessage import TranslationMessage


class ComponentVocabulary(SQLObjectVocabularyBase):

    _table = Component
    _orderBy = 'name'

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.name)


# Country.name may have non-ASCII characters, so we can't use
# NamedSQLObjectVocabulary here.

class CountryNameVocabulary(SQLObjectVocabularyBase):
    """A vocabulary for country names."""

    _table = Country
    _orderBy = 'name'

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.name)


class LanguageVocabulary(SQLObjectVocabularyBase):
    """All the languages known by Launchpad."""

    _table = Language
    _orderBy = 'englishname'

    def __contains__(self, language):
        """See `IVocabulary`."""
        assert ILanguage.providedBy(language), (
            "'in LanguageVocabulary' requires ILanguage as left operand, "
            "got %s instead." % type(language))
        return super(LanguageVocabulary, self).__contains__(language)

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.code, obj.displayname)

    def getTerm(self, obj):
        """See `IVocabulary`."""
        if obj not in self:
            raise LookupError(obj)
        return SimpleTerm(obj, obj.code, obj.displayname)

    def getTermByToken(self, token):
        """See `IVocabulary`."""
        try:
            found_language = Language.byCode(token)
        except SQLObjectNotFound:
            raise LookupError(token)
        return self.getTerm(found_language)


class TranslatableLanguageVocabulary(LanguageVocabulary):
    """All the translatable languages known by Launchpad.

    Messages cannot be translated into English or a non-visible language.
    This vocabulary contains all the languages known to Launchpad,
    excluding English and non-visible languages.
    """

    def __contains__(self, language):
        """See `IVocabulary`.

        This vocabulary excludes English and languages that are not visible.
        """
        assert ILanguage.providedBy(language), (
            "'in TranslatableLanguageVocabulary' requires ILanguage as "
            "left operand, got %s instead." % type(language))
        if language.code == 'en':
            return False
        return language.visible == True and super(
            TranslatableLanguageVocabulary, self).__contains__(language)

    def __iter__(self):
        """See `IVocabulary`.

        Iterate languages that are visible and not English.
        """
        languages = self._table.select(
            "Language.code != 'en' AND Language.visible = True",
            orderBy=self._orderBy)
        for language in languages:
            yield self.toTerm(language)

    def getTermByToken(self, token):
        """See `IVocabulary`."""
        if token == 'en':
            raise LookupError(token)
        term = super(TranslatableLanguageVocabulary, self).getTermByToken(
            token)
        if not term.value.visible:
            raise LookupError(token)
        return term


class TranslationGroupVocabulary(NamedSQLObjectVocabulary):

    _table = TranslationGroup


class TranslationMessageVocabulary(SQLObjectVocabularyBase):

    _table = TranslationMessage
    _orderBy = 'date_created'

    def toTerm(self, obj):
        translation = ''
        if obj.msgstr0 is not None:
            translation = obj.msgstr0.translation
        return SimpleTerm(obj, obj.id, translation)

    def __iter__(self):
        for message in self.context.messages:
            yield self.toTerm(message)


class TranslationTemplateVocabulary(SQLObjectVocabularyBase):
    """The set of all POTemplates for a given product or package."""

    _table = POTemplate
    _orderBy = 'name'

    def __init__(self, context):
        if context.productseries != None:
            self._filter = AND(
                POTemplate.iscurrent == True,
                POTemplate.productseries == context.productseries)
        else:
            self._filter = AND(
                POTemplate.iscurrent == True,
                POTemplate.distroseries == context.distroseries,
                POTemplate.sourcepackagename == context.sourcepackagename)
        super(TranslationTemplateVocabulary, self).__init__(context)

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.name)


class FilteredDistroArchSeriesVocabulary(SQLObjectVocabularyBase):
    """All arch series of a particular distribution."""

    _table = DistroArchSeries
    _orderBy = ['DistroSeries.version', 'architecturetag', 'id']
    _clauseTables = ['DistroSeries']

    def toTerm(self, obj):
        name = "%s %s (%s)" % (obj.distroseries.distribution.name,
                               obj.distroseries.name, obj.architecturetag)
        return SimpleTerm(obj, obj.id, name)

    def __iter__(self):
        distribution = getUtility(ILaunchBag).distribution
        if distribution:
            query = """
                DistroSeries.id = DistroArchSeries.distroseries AND
                DistroSeries.distribution = %s
                """ % sqlvalues(distribution.id)
            results = self._table.select(
                query, orderBy=self._orderBy, clauseTables=self._clauseTables)
            for distroarchseries in results:
                yield self.toTerm(distroarchseries)


class PackageReleaseVocabulary(SQLObjectVocabularyBase):
    _table = SourcePackageRelease
    _orderBy = 'id'

    def toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.name + " " + obj.version)


class PPAVocabulary(SQLObjectVocabularyBase):

    implements(IHugeVocabulary)

    _table = Archive
    _orderBy = ['Person.name, Archive.name']
    _clauseTables = ['Person']
    _filter = AND(
        Person.q.id == Archive.q.ownerID,
        Archive.q.purpose == ArchivePurpose.PPA)
    displayname = 'Select a PPA'
    step_title = 'Search'

    def toTerm(self, archive):
        """See `IVocabulary`."""
        description = archive.description
        if description is not None:
            summary = description.splitlines()[0]
        else:
            summary = "No description available"

        token = '%s/%s' % (archive.owner.name, archive.name)

        return SimpleTerm(archive, token, summary)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        try:
            owner_name, archive_name = token.split('/')
        except ValueError:
            raise LookupError(token)

        clause = AND(
            self._filter,
            Person.name == owner_name,
            Archive.name == archive_name)

        obj = self._table.selectOne(
            clause, clauseTables=self._clauseTables)

        if obj is None:
            raise LookupError(token)
        else:
            return self.toTerm(obj)

    def search(self, query, vocab_filter=None):
        """Return a resultset of archives.

        This is a helper required by `SQLObjectVocabularyBase.searchForTerms`.
        """
        if not query:
            return self.emptySelectResults()

        query = query.lower()

        try:
            owner_name, archive_name = query.split('/')
        except ValueError:
            clause = AND(
                self._filter,
                SQL("(Archive.fti @@ ftq(%s) OR Person.fti @@ ftq(%s))"
                    % (quote(query), quote(query))))
        else:
            clause = AND(
                self._filter,
                Person.name == owner_name,
                Archive.name == archive_name)

        return self._table.select(
            clause, orderBy=self._orderBy, clauseTables=self._clauseTables)


class ProcessorVocabulary(NamedSQLObjectVocabulary):

    displayname = 'Select a processor'
    _table = Processor
    _orderBy = 'name'


class ProcessorFamilyVocabulary(NamedSQLObjectVocabulary):
    displayname = 'Select a processor family'
    _table = ProcessorFamily
    _orderBy = 'name'


class FilteredLanguagePackVocabularyBase(SQLObjectVocabularyBase):
    """Base vocabulary class to retrieve language packs for a distroseries."""
    _table = LanguagePack
    _orderBy = '-date_exported'

    def toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, '%s' % obj.date_exported.strftime('%F %T %Z'))

    def _baseQueryList(self):
        """Return a list of sentences that defines the specific filtering.

        That list will be linked with an ' AND '.
        """
        raise NotImplementedError

    def __iter__(self):
        if not IDistroSeries.providedBy(self.context):
            # This vocabulary is only useful from a DistroSeries context.
            return

        query = self._baseQueryList()
        query.append('distroseries = %s' % sqlvalues(self.context))
        language_packs = self._table.select(
            ' AND '.join(query), orderBy=self._orderBy)

        for language_pack in language_packs:
            yield self.toTerm(language_pack)


class FilteredFullLanguagePackVocabulary(FilteredLanguagePackVocabularyBase):
    """Full export Language Pack for a distribution series."""
    displayname = 'Select a full export language pack'

    def _baseQueryList(self):
        """See `FilteredLanguagePackVocabularyBase`."""
        return ['type = %s' % sqlvalues(LanguagePackType.FULL)]


class FilteredDeltaLanguagePackVocabulary(FilteredLanguagePackVocabularyBase):
    """Delta export Language Pack for a distribution series."""
    displayname = 'Select a delta export language pack'

    def _baseQueryList(self):
        """See `FilteredLanguagePackVocabularyBase`."""
        return ['(type = %s AND updates = %s)' % sqlvalues(
            LanguagePackType.DELTA, self.context.language_pack_base)]


class FilteredLanguagePackVocabulary(FilteredLanguagePackVocabularyBase):
    displayname = 'Select a language pack'

    def toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, '%s (%s)' % (
                obj.date_exported.strftime('%F %T %Z'), obj.type.title))

    def _baseQueryList(self):
        """See `FilteredLanguagePackVocabularyBase`."""
        # We are interested on any full language pack or language pack
        # that is a delta of the current base lanuage pack type,
        # except the ones already used.
        used_lang_packs = []
        if self.context.language_pack_base is not None:
            used_lang_packs.append(self.context.language_pack_base.id)
        if self.context.language_pack_delta is not None:
            used_lang_packs.append(self.context.language_pack_delta.id)
        query = []
        if used_lang_packs:
            query.append('id NOT IN %s' % sqlvalues(used_lang_packs))
        query.append('(updates is NULL OR updates = %s)' % sqlvalues(
            self.context.language_pack_base))
        return query
