# Copyright 2004-2009 Canonical Ltd.  All rights reserved.

"""Vocabularies pulling stuff from the database.

You probably don't want to use these classes directly - see the
docstring in __init__.py for details.
"""

__metaclass__ = type

__all__ = [
    'BountyVocabulary',
    'BranchRestrictedOnProductVocabulary',
    'BranchVocabulary',
    'BugNominatableSeriesesVocabulary',
    'BugTrackerVocabulary',
    'BugVocabulary',
    'BugWatchVocabulary',
    'ComponentVocabulary',
    'CountryNameVocabulary',
    'DistributionUsingMaloneVocabulary',
    'FilteredDeltaLanguagePackVocabulary',
    'FilteredDistroArchSeriesVocabulary',
    'FilteredFullLanguagePackVocabulary',
    'FilteredLanguagePackVocabulary',
    'FutureSprintVocabulary',
    'LanguageVocabulary',
    'PPAVocabulary',
    'PackageReleaseVocabulary',
    'ProcessorFamilyVocabulary',
    'ProcessorVocabulary',
    'SpecificationDepCandidatesVocabulary',
    'SpecificationDependenciesVocabulary',
    'SpecificationVocabulary',
    'SprintVocabulary',
    'TranslatableLanguageVocabulary',
    'TranslationGroupVocabulary',
    'TranslationMessageVocabulary',
    'TranslationTemplateVocabulary',
    'WebBugTrackerVocabulary',
    'project_products_using_malone_vocabulary_factory',
    ]

import cgi
from operator import attrgetter

from sqlobject import AND, SQLObjectNotFound
from storm.expr import SQL
from zope.component import getUtility
from zope.interface import implements
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.launchpad.database import (
    Archive, Bounty, Branch, Bug, BugTracker, BugWatch, Component, Country,
    Distribution, DistroArchSeries, DistroSeries, Language, LanguagePack,
    Person, POTemplate, Processor, ProcessorFamily, ProductSeries,
    SourcePackageRelease, Specification, Sprint, TranslationGroup,
    TranslationMessage)
from canonical.database.sqlbase import quote_like, quote, sqlvalues
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import IStore
from lp.soyuz.interfaces.archive import ArchivePurpose
from canonical.launchpad.interfaces.bugtask import IBugTask
from canonical.launchpad.interfaces.bugtracker import BugTrackerType
from lp.services.worlddata.interfaces.language import ILanguage
from canonical.launchpad.interfaces.languagepack import LanguagePackType
from lp.blueprints.interfaces.specification import SpecificationFilter
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.tales import FormattersAPI
from canonical.launchpad.webapp.vocabulary import (
    CountableIterator, IHugeVocabulary,
    NamedSQLObjectVocabulary, SQLObjectVocabularyBase)

from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branchcollection import IAllBranches
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import (
    DistroSeriesStatus, IDistroSeries)
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.project import IProject

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


class BranchVocabularyBase(SQLObjectVocabularyBase):
    """A base class for Branch vocabularies.

    Override `BranchVocabularyBase._getCollection` to provide the collection
    of branches which make up the vocabulary.
    """

    implements(IHugeVocabulary)

    _table = Branch
    _orderBy = ['name', 'id']
    displayname = 'Select a Branch'

    def toTerm(self, branch):
        """The display should include the URL if there is one."""
        return SimpleTerm(branch, branch.unique_name, branch.displayname)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        search_results = self.searchForTerms(token)
        if search_results.count() == 1:
            return iter(search_results).next()
        raise LookupError(token)

    def _getCollection(self):
        """Override this to return the collection to which the search is
        restricted.
        """
        raise NotImplementedError(self._getCollection)

    def searchForTerms(self, query=None):
        """See `IHugeVocabulary`."""
        logged_in_user = getUtility(ILaunchBag).user
        collection = self._getCollection().visibleByUser(logged_in_user)
        if query is None:
            branches = collection.getBranches()
        else:
            branches = collection.search(query)
        return CountableIterator(branches.count(), branches, self.toTerm)

    def __len__(self):
        """See `IVocabulary`."""
        return self.search().count()


class BranchVocabulary(BranchVocabularyBase):
    """A vocabulary for searching branches.

    The name and URL of the branch, the name of the product, and the
    name of the registrant of the branches is checked for the entered
    value.
    """

    def _getCollection(self):
        return getUtility(IAllBranches)


class BranchRestrictedOnProductVocabulary(BranchVocabularyBase):
    """A vocabulary for searching branches restricted on product.

    The query entered checks the name or URL of the branch, or the
    name of the registrant of the branch.
    """

    def __init__(self, context=None):
        BranchVocabularyBase.__init__(self, context)
        if IProduct.providedBy(self.context):
            self.product = self.context
        elif IProductSeries.providedBy(self.context):
            self.product = self.context.product
        elif IBranch.providedBy(self.context):
            self.product = self.context.product
        else:
            # An unexpected type.
            raise AssertionError('Unexpected context type')

    def _getCollection(self):
        return getUtility(IAllBranches).inProduct(self.product)


class BugVocabulary(SQLObjectVocabularyBase):

    _table = Bug
    _orderBy = 'id'


class BountyVocabulary(SQLObjectVocabularyBase):

    _table = Bounty
    # XXX kiko 2006-02-20: no _orderBy?


class BugTrackerVocabulary(SQLObjectVocabularyBase):

    _table = BugTracker
    _orderBy = 'title'


class WebBugTrackerVocabulary(BugTrackerVocabulary):
    """All web-based bug tracker types."""

    _filter = BugTracker.q.bugtrackertype != BugTrackerType.EMAILADDRESS


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


def project_products_using_malone_vocabulary_factory(context):
    """Return a vocabulary containing a project's products using Malone."""
    project = IProject(context)
    return SimpleVocabulary([
        SimpleTerm(product, product.name, title=product.displayname)
        for product in project.products
        if product.official_malone])


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
                POTemplate.productseries == context.productseries
            )
        else:
            self._filter = AND(
                POTemplate.iscurrent == True,
                POTemplate.distroseries == context.distroseries,
                POTemplate.sourcepackagename == context.sourcepackagename
            )
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


class FutureSprintVocabulary(NamedSQLObjectVocabulary):
    """A vocab of all sprints that have not yet finished."""

    _table = Sprint

    def __iter__(self):
        future_sprints = Sprint.select("time_ends > 'NOW'")
        for sprint in future_sprints:
            yield(self.toTerm(sprint))


class SpecificationVocabulary(NamedSQLObjectVocabulary):
    """List specifications for the current product or distribution in
    ILaunchBag, EXCEPT for the current spec in LaunchBag if one exists.
    """

    _table = Specification
    _orderBy = 'title'

    def __iter__(self):
        launchbag = getUtility(ILaunchBag)
        target = None
        product = launchbag.product
        if product is not None:
            target = product

        distribution = launchbag.distribution
        if distribution is not None:
            target = distribution

        if target is not None:
            for spec in sorted(
                target.specifications(), key=attrgetter('title')):
                # we will not show the current specification in the
                # launchbag
                if spec == launchbag.specification:
                    continue
                # we will not show a specification that is blocked on the
                # current specification in the launchbag. this is because
                # the widget is currently used to select new dependencies,
                # and we do not want to introduce circular dependencies.
                if launchbag.specification is not None:
                    if spec in launchbag.specification.all_blocked:
                        continue
                yield SimpleTerm(spec, spec.name, spec.title)


class SpecificationDependenciesVocabulary(NamedSQLObjectVocabulary):
    """List specifications on which the current specification depends."""

    _table = Specification
    _orderBy = 'title'

    def __iter__(self):
        launchbag = getUtility(ILaunchBag)
        curr_spec = launchbag.specification

        if curr_spec is not None:
            for spec in sorted(
                curr_spec.dependencies, key=attrgetter('title')):
                yield SimpleTerm(spec, spec.name, spec.title)


class SpecificationDepCandidatesVocabulary(SQLObjectVocabularyBase):
    """Specifications that could be dependencies of this spec.

    This includes only those specs that are not blocked by this spec
    (directly or indirectly), unless they are already dependencies.

    The current spec is not included.
    """

    implements(IHugeVocabulary)

    _table = Specification
    _orderBy = 'name'
    displayname = 'Select a blueprint'

    def _filter_specs(self, specs):
        # XXX intellectronica 2007-07-05: is 100 a reasonable count before
        # starting to warn?
        speclist = shortlist(specs, 100)
        return [spec for spec in speclist
                if (spec != self.context and
                    spec.target == self.context.target
                    and spec not in self.context.all_blocked)]

    def _doSearch(self, query):
        """Return terms where query is in the text of name
        or title, or matches the full text index.
        """

        if not query:
            return []

        quoted_query = quote_like(query)
        sql_query = ("""
            (Specification.name LIKE %s OR
             Specification.title LIKE %s OR
             fti @@ ftq(%s))
            """
            % (quoted_query, quoted_query, quoted_query))
        all_specs = Specification.select(sql_query, orderBy=self._orderBy)

        return self._filter_specs(all_specs)

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        search_results = self._doSearch(token)
        for search_result in search_results:
            if search_result.name == token:
                return self.toTerm(search_result)
        raise LookupError(token)

    def search(self, query):
        candidate_specs = self._doSearch(query)
        return CountableIterator(len(candidate_specs),
                                 candidate_specs)

    def _all_specs(self):
        all_specs = self.context.target.specifications(
            filter=[SpecificationFilter.ALL],
            prejoin_people=False)
        return self._filter_specs(all_specs)

    def __iter__(self):
        return (self.toTerm(spec) for spec in self._all_specs())

    def __contains__(self, obj):
        # We don't use self._all_specs here, since it will call
        # self._filter_specs(all_specs) which will cause all the specs
        # to be loaded, whereas obj in all_specs will query a single object.
        all_specs = self.context.target.specifications(
            filter=[SpecificationFilter.ALL],
            prejoin_people=False)
        return obj in all_specs and len(self._filter_specs([obj])) > 0


class SprintVocabulary(NamedSQLObjectVocabulary):
    _table = Sprint


class BugWatchVocabulary(SQLObjectVocabularyBase):
    _table = BugWatch

    def __iter__(self):
        assert IBugTask.providedBy(self.context), (
            "BugWatchVocabulary expects its context to be an IBugTask.")
        bug = self.context.bug

        for watch in bug.watches:
            yield self.toTerm(watch)

    def toTerm(self, watch):
        def escape(string):
            return cgi.escape(string, quote=True)

        if watch.url.startswith('mailto:'):
            user = getUtility(ILaunchBag).user
            if user is None:
                title = FormattersAPI(
                    watch.bugtracker.title).obfuscate_email()
                return SimpleTerm(
                    watch, watch.id, escape(title))
            else:
                url = watch.url
                title = escape(watch.bugtracker.title)
                if url in title:
                    title = title.replace(
                        url, '<a href="%s">%s</a>' % (
                            escape(url), escape(url)))
                else:
                    title = '%s &lt;<a href="%s">%s</a>&gt;' % (
                        title, escape(url), escape(url[7:]))
                return SimpleTerm(watch, watch.id, title)
        else:
            return SimpleTerm(
                watch, watch.id, '%s <a href="%s">#%s</a>' % (
                    escape(watch.bugtracker.title),
                    escape(watch.url),
                    escape(watch.remotebug)))


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

    def search(self, query):
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


class DistributionUsingMaloneVocabulary:
    """All the distributions that uses Malone officially."""

    implements(IVocabulary, IVocabularyTokenized)

    _orderBy = 'displayname'

    def __init__(self, context=None):
        self.context = context

    def __iter__(self):
        """Return an iterator which provides the terms from the vocabulary."""
        distributions_using_malone = Distribution.selectBy(
            official_malone=True, orderBy=self._orderBy)
        for distribution in distributions_using_malone:
            yield self.getTerm(distribution)

    def __len__(self):
        return Distribution.selectBy(official_malone=True).count()

    def __contains__(self, obj):
        return IDistribution.providedBy(obj) and obj.official_malone

    def getQuery(self):
        return None

    def getTerm(self, obj):
        if obj not in self:
            raise LookupError(obj)
        return SimpleTerm(obj, obj.name, obj.displayname)

    def getTermByToken(self, token):
        found_dist = Distribution.selectOneBy(
            name=token, official_malone=True)
        if found_dist is None:
            raise LookupError(token)
        return self.getTerm(found_dist)


class ProcessorVocabulary(NamedSQLObjectVocabulary):

    displayname = 'Select a Processor'
    _table = Processor
    _orderBy = 'name'


class ProcessorFamilyVocabulary(NamedSQLObjectVocabulary):
    displayname = 'Select a Processor Family'
    _table = ProcessorFamily
    _orderBy = 'name'


def BugNominatableSeriesesVocabulary(context=None):
    """Return a nominatable serieses vocabulary."""

    if getUtility(ILaunchBag).distribution:
        return BugNominatableDistroSeriesVocabulary(
            context, getUtility(ILaunchBag).distribution)
    else:
        assert getUtility(ILaunchBag).product
        return BugNominatableProductSeriesVocabulary(
            context, getUtility(ILaunchBag).product)


class BugNominatableSeriesVocabularyBase(NamedSQLObjectVocabulary):
    """Base vocabulary class for series for which a bug can be nominated."""

    def __iter__(self):
        bug = self.context.bug

        serieses = self._getNominatableObjects()

        for series in sorted(serieses, key=attrgetter("displayname")):
            if bug.canBeNominatedFor(series):
                yield self.toTerm(series)

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.name.capitalize())

    def getTermByToken(self, token):
        obj = self._queryNominatableObjectByName(token)
        if obj is None:
            raise LookupError(token)

        return self.toTerm(obj)

    def _getNominatableObjects(self):
        """Return the series objects that the bug can be nominated for."""
        raise NotImplementedError

    def _queryNominatableObjectByName(self, name):
        """Return the series object with the given name."""
        raise NotImplementedError


class BugNominatableProductSeriesVocabulary(
    BugNominatableSeriesVocabularyBase):
    """The product series for which a bug can be nominated."""

    _table = ProductSeries

    def __init__(self, context, product):
        BugNominatableSeriesVocabularyBase.__init__(self, context)
        self.product = product

    def _getNominatableObjects(self):
        """See BugNominatableSeriesVocabularyBase."""
        return shortlist(self.product.serieses)

    def _queryNominatableObjectByName(self, name):
        """See BugNominatableSeriesVocabularyBase."""
        return self.product.getSeries(name)


class BugNominatableDistroSeriesVocabulary(
    BugNominatableSeriesVocabularyBase):
    """The distribution series for which a bug can be nominated."""

    _table = DistroSeries

    def __init__(self, context, distribution):
        BugNominatableSeriesVocabularyBase.__init__(self, context)
        self.distribution = distribution

    def _getNominatableObjects(self):
        """Return all non-obsolete distribution serieses"""
        return [
            series for series in shortlist(self.distribution.serieses)
            if series.status != DistroSeriesStatus.OBSOLETE]

    def _queryNominatableObjectByName(self, name):
        """See BugNominatableSeriesVocabularyBase."""
        return self.distribution.getSeries(name)


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
