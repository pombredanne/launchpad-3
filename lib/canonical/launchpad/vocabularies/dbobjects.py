# Copyright 2004-2009 Canonical Ltd.  All rights reserved.

"""Vocabularies pulling stuff from the database.

You probably don't want to use these classes directly - see the
docstring in __init__.py for details.
"""

__metaclass__ = type

__all__ = [
    'ActiveMailingListVocabulary',
    'BountyVocabulary',
    'BranchRestrictedOnProductVocabulary',
    'BranchVocabulary',
    'BugNominatableSeriesesVocabulary',
    'BugTrackerVocabulary',
    'BugVocabulary',
    'BugWatchVocabulary',
    'CommercialProjectsVocabulary',
    'ComponentVocabulary',
    'CountryNameVocabulary',
    'DistributionOrProductOrProjectVocabulary',
    'DistributionOrProductVocabulary',
    'DistributionUsingMaloneVocabulary',
    'DistributionVocabulary',
    'DistroSeriesVocabulary',
    'FeaturedProjectVocabulary',
    'FilteredDeltaLanguagePackVocabulary',
    'FilteredDistroArchSeriesVocabulary',
    'FilteredDistroSeriesVocabulary',
    'FilteredFullLanguagePackVocabulary',
    'FilteredLanguagePackVocabulary',
    'FilteredProductSeriesVocabulary',
    'FutureSprintVocabulary',
    'KarmaCategoryVocabulary',
    'LanguageVocabulary',
    'MilestoneVocabulary',
    'NonMergedPeopleAndTeamsVocabulary',
    'PPAVocabulary',
    'PackageReleaseVocabulary',
    'PersonAccountToMergeVocabulary',
    'PersonActiveMembershipVocabulary',
    'ProcessorFamilyVocabulary',
    'ProcessorVocabulary',
    'ProductReleaseVocabulary',
    'ProductSeriesVocabulary',
    'ProductVocabulary',
    'ProjectVocabulary',
    'SpecificationDepCandidatesVocabulary',
    'SpecificationDependenciesVocabulary',
    'SpecificationVocabulary',
    'SprintVocabulary',
    'TranslatableLanguageVocabulary',
    'TranslationGroupVocabulary',
    'TranslationMessageVocabulary',
    'TranslationTemplateVocabulary',
    'UserTeamsParticipationVocabulary',
    'UserTeamsParticipationPlusSelfVocabulary',
    'ValidPersonOrTeamVocabulary',
    'ValidPersonVocabulary',
    'ValidTeamMemberVocabulary',
    'ValidTeamOwnerVocabulary',
    'ValidTeamVocabulary',
    'WebBugTrackerVocabulary',
    'person_team_participations_vocabulary_factory',
    'project_products_using_malone_vocabulary_factory',
    'project_products_vocabulary_factory',
    ]

import cgi
from operator import attrgetter

from sqlobject import AND, CONTAINSSTRING, OR, SQLObjectNotFound
from storm.expr import LeftJoin, SQL, And, Or, Not
from zope.component import getUtility
from zope.interface import implements
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.security.proxy import isinstance as zisinstance
from zope.security.proxy import removeSecurityProxy

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.database import (
    Account, Archive, Bounty, Branch, Bug, BugTracker, BugWatch, Component,
    Country, Distribution, DistroArchSeries, DistroSeries, EmailAddress,
    FeaturedProject, KarmaCategory, Language, LanguagePack, MailingList,
    Milestone, Person, PillarName, POTemplate, Processor, ProcessorFamily,
    Product, ProductRelease, ProductSeries, Project, SourcePackageRelease,
    Specification, Sprint, TranslationGroup, TranslationMessage)
from canonical.database.sqlbase import SQLBase, quote_like, quote, sqlvalues
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import IStore
from canonical.launchpad.interfaces.archive import ArchivePurpose
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branchcollection import IAllBranches
from canonical.launchpad.interfaces.bugtask import (
    IBugTask, IDistroBugTask, IDistroSeriesBugTask, IProductSeriesBugTask,
    IUpstreamBugTask)
from canonical.launchpad.interfaces.bugtracker import BugTrackerType
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
from lp.registry.interfaces.distroseries import (
    DistroSeriesStatus, IDistroSeries)
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.language import ILanguage
from canonical.launchpad.interfaces.languagepack import LanguagePackType
from lp.registry.interfaces.mailinglist import (
    IMailingListSet, MailingListStatus)
from lp.registry.interfaces.milestone import (
    IMilestoneSet, IProjectMilestone)
from lp.registry.interfaces.person import (
    IPerson, IPersonSet, ITeam, PersonVisibility)
from lp.registry.interfaces.pillar import IPillarName
from lp.registry.interfaces.product import (
    IProduct, IProductSet, License)
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.project import IProject
from lp.registry.interfaces.sourcepackage import ISourcePackage
from canonical.launchpad.interfaces.specification import (
    ISpecification, SpecificationFilter)
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import (
    ILaunchBag, IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.launchpad.webapp.tales import (
    DateTimeFormatterAPI, FormattersAPI)
from canonical.launchpad.webapp.vocabulary import (
    CountableIterator, IHugeVocabulary, NamedSQLObjectHugeVocabulary,
    NamedSQLObjectVocabulary, SQLObjectVocabularyBase)


class BasePersonVocabulary:
    """This is a base class used by all different Person Vocabularies."""

    _table = Person

    def toTerm(self, obj):
        """Return the term for this object."""
        return SimpleTerm(obj, obj.name, obj.browsername)

    def getTermByToken(self, token):
        """Return the term for the given token.

        If the token contains an '@', treat it like an email. Otherwise,
        treat it like a name.
        """
        if "@" in token:
            # This looks like an email token, so let's do an object
            # lookup based on that.
            # We retrieve the email address via the main store, so 
            # we can easily traverse to email.person to retrieve the
            # result from the main Store as expected by our call sites.
            email = IStore(Person).find(
                EmailAddress,
                EmailAddress.email.lower() == token.strip().lower()).one()
            if email is None:
                raise LookupError(token)
            return self.toTerm(email.person)
        else:
            # This doesn't look like an email, so let's simply treat
            # it like a name.
            person = getUtility(IPersonSet).getByName(token)
            if person is None:
                raise LookupError(token)
            return self.toTerm(person)


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


class KarmaCategoryVocabulary(NamedSQLObjectVocabulary):

    _table = KarmaCategory
    _orderBy = 'name'


# XXX kiko 2007-01-18: any reason why this can't be an
# NamedSQLObjectHugeVocabulary?
class ProductVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = Product
    _orderBy = 'displayname'
    displayname = 'Select a project'

    def __contains__(self, obj):
        # Sometimes this method is called with an SQLBase instance, but
        # z3 form machinery sends through integer ids. This might be due
        # to a bug somewhere.
        where = "active='t' AND id=%d"
        if zisinstance(obj, SQLBase):
            product = self._table.selectOne(where % obj.id)
            return product is not None and product == obj
        else:
            product = self._table.selectOne(where % int(obj))
            return product is not None

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        product = self._table.selectOneBy(name=token, active=True)
        if product is None:
            raise LookupError(token)
        return self.toTerm(product)

    def search(self, query):
        """Returns products where the product name, displayname, title,
        summary, or description contain the given query. Returns an empty list
        if query is None or an empty string.
        """
        if query:
            query = query.lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
            fti_query = quote(query)
            sql = "active = 't' AND (name LIKE %s OR fti @@ ftq(%s))" % (
                    like_query, fti_query
                    )
            return self._table.select(sql, orderBy=self._orderBy)
        return self.emptySelectResults()


# XXX kiko 2007-01-18: any reason why this can't be an
# NamedSQLObjectHugeVocabulary?
class ProjectVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = Project
    _orderBy = 'displayname'
    displayname = 'Select a project group'

    def __contains__(self, obj):
        where = "active='t' and id=%d"
        if zisinstance(obj, SQLBase):
            project = self._table.selectOne(where % obj.id)
            return project is not None and project == obj
        else:
            project = self._table.selectOne(where % int(obj))
            return project is not None

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        project = self._table.selectOneBy(name=token, active=True)
        if project is None:
            raise LookupError(token)
        return self.toTerm(project)

    def search(self, query):
        """Returns projects where the project name, displayname, title,
        summary, or description contain the given query. Returns an empty list
        if query is None or an empty string.
        """
        if query:
            query = query.lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
            fti_query = quote(query)
            sql = "active = 't' AND (name LIKE %s OR fti @@ ftq(%s))" % (
                    like_query, fti_query
                    )
            return self._table.select(sql)
        return self.emptySelectResults()


def project_products_vocabulary_factory(context):
    """Return a SimpleVocabulary containing the project's products."""
    assert context is not None
    project = IProject(context)
    return SimpleVocabulary([
        SimpleTerm(product, product.name, title=product.displayname)
        for product in project.products])


class UserTeamsParticipationVocabulary(SQLObjectVocabularyBase):
    """Describes the teams in which the current user participates."""
    _table = Person
    _orderBy = 'displayname'

    def toTerm(self, obj):
        return SimpleTerm(
            obj, obj.name, '%s (%s)' % (obj.displayname, obj.name))

    def __iter__(self):
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        launchbag = getUtility(ILaunchBag)
        if launchbag.user:
            user = launchbag.user
            for team in user.teams_participated_in:
                if team.visibility == PersonVisibility.PUBLIC:
                    yield self.toTerm(team)

    def getTermByToken(self, token):
        launchbag = getUtility(ILaunchBag)
        if launchbag.user:
            user = launchbag.user
            for team in user.teams_participated_in:
                if team.name == token:
                    return self.getTerm(team)
        raise LookupError(token)


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


class NonMergedPeopleAndTeamsVocabulary(
        BasePersonVocabulary, SQLObjectVocabularyBase):
    """The set of all non-merged people and teams.

    If you use this vocabulary you need to make sure that any code which uses
    the people provided by it know how to deal with people which don't have
    a preferred email address, that is, unvalidated person profiles.
    """
    implements(IHugeVocabulary)

    _orderBy = ['displayname']
    displayname = 'Select a Person or Team'

    def __contains__(self, obj):
        return obj in self._select()

    def _select(self, text=""):
        return getUtility(IPersonSet).find(text)

    def search(self, text):
        """Return people/teams whose fti or email address match :text."""
        if not text:
            return self.emptySelectResults()

        return self._select(text.lower())


class PersonAccountToMergeVocabulary(
        BasePersonVocabulary, SQLObjectVocabularyBase):
    """The set of all non-merged people with at least one email address.

    This vocabulary is a very specialized one, meant to be used only to choose
    accounts to merge. You *don't* want to use it.
    """
    implements(IHugeVocabulary)

    _orderBy = ['displayname']
    displayname = 'Select a Person to Merge'

    def __contains__(self, obj):
        return obj in self._select()

    def _select(self, text=""):
        return getUtility(IPersonSet).findPerson(
            text, exclude_inactive_accounts=False, must_have_email=True)

    def search(self, text):
        """Return people whose fti or email address match :text."""
        if not text:
            return self.emptySelectResults()

        text = text.lower()
        return self._select(text)


class ValidPersonOrTeamVocabulary(
        BasePersonVocabulary, SQLObjectVocabularyBase):
    """The set of valid, public Persons/Teams in Launchpad.

    A Person is considered valid if he has a preferred email address,
    and Person.merged is None. Teams have no restrictions
    at all, which means that all teams are considered valid.

    This vocabulary is registered as ValidPersonOrTeam, ValidAssignee,
    ValidMaintainer and ValidOwner, because they have exactly the same
    requisites.
    """
    implements(IHugeVocabulary)

    displayname = 'Select a Person or Team'

    # This is what subclasses must change if they want any extra filtering of
    # results.
    extra_clause = ""

    # Subclasses should override this property to allow null searches to
    # return all results.  If false, an empty result set is returned.
    allow_null_search = False

    # Cache table to use for checking validity.
    cache_table_name = 'ValidPersonOrTeamCache'

    def __contains__(self, obj):
        return obj in self._doSearch()

    def _doSearch(self, text=""):
        """Return the people/teams whose fti or email address match :text:"""

        # Short circuit if there is no search text - all valid people and
        # teams have been requested.
        if not text:
            query = """
                Person.id = %s.id
                AND Person.visibility = %s
                """ % (self.cache_table_name,
                       quote(PersonVisibility.PUBLIC))
            if self.extra_clause:
                query += " AND %s" % self.extra_clause
            return Person.select(
                query, clauseTables=[self.cache_table_name])

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        tables = [
            Person,
            LeftJoin(EmailAddress, EmailAddress.person == Person.id),
            LeftJoin(Account, EmailAddress.account == Account.id),
            ]

        # Note we use lower() instead of the non-standard ILIKE because
        # ILIKE doesn't seem to hit the indexes.
        inner_select = SQL("""
            SELECT Person.id
            FROM Person
            WHERE Person.fti @@ ftq(%s)
            UNION ALL
            SELECT Person.id
            FROM Person, IrcId
            WHERE IrcId.person = Person.id
                AND lower(IrcId.nickname) = %s
            UNION ALL
            SELECT Person.id
            FROM Person, EmailAddress
            WHERE EmailAddress.person = Person.id
                AND lower(email) LIKE %s || '%%%%'
                AND EmailAddress.status IN %s
            """ % (
                quote(text), quote(text), quote_like(text),
                sqlvalues(
                    EmailAddressStatus.VALIDATED,
                    EmailAddressStatus.PREFERRED)))

        if self.extra_clause:
            extra_clause = SQL(self.extra_clause)
        else:
            extra_clause = True
        result = store.using(*tables).find(
            Person,
            And(
                Person.id.is_in(inner_select),
                Person.visibility == PersonVisibility.PUBLIC,
                Person.merged == None,
                Or(
                    # A valid person-or-team is either a team...
                    Not(Person.teamowner == None), # 'Not' due to Bug 244768

                    # or has an active account and a working email address.
                    And(
                        Account.status == AccountStatus.ACTIVE,
                        EmailAddress.status.is_in((
                            EmailAddressStatus.VALIDATED,
                            EmailAddressStatus.PREFERRED
                            ))
                        )
                    ),
                extra_clause
                )
            )
        result.config(distinct=True)
        # XXX: salgado, 2008-07-23: Sorting by Person.sortingColumns would
        # make this run a lot faster, but I couldn't find how to do that
        # because this query uses distinct=True.
        return result.order_by(Person.displayname, Person.name)

    def search(self, text):
        """Return people/teams whose fti or email address match :text:."""
        if not text:
            if self.allow_null_search:
                text = ''
            else:
                return self.emptySelectResults()

        text = text.lower()
        return self._doSearch(text=text)

class ValidTeamVocabulary(ValidPersonOrTeamVocabulary):
    """The set of all valid, public teams in Launchpad."""

    displayname = 'Select a Team'

    # XXX: BradCrittenden 2008-08-11 bug=255798: This method does not return
    # only the valid teams as the name implies because it does not account for
    # merged teams.

    # Because the base class does almost everything we need, we just need to
    # restrict the search results to those Persons who have a non-NULL
    # teamowner, i.e. a valid team.
    extra_clause = 'Person.teamowner IS NOT NULL'
    # Search with empty string returns all teams.
    allow_null_search = True

    def _doSearch(self, text=""):
        """Return the teams whose fti or email address match :text:"""
        base_query = """
                Person.visibility = %s
                """ % quote(PersonVisibility.PUBLIC)

        if self.extra_clause:
            extra_clause = " AND %s" % self.extra_clause
        else:
            extra_clause = ""

        if not text:
            query = base_query + extra_clause
            return Person.select(query)

        name_match_query = """
            Person.fti @@ ftq(%s)
            AND %s
            """ % (quote(text), base_query)
        name_match_query += extra_clause
        name_matches = Person.select(name_match_query)

        # Note that we must use lower(email) LIKE rather than ILIKE
        # as ILIKE no longer appears to be hitting the index under PG8.0

        email_match_query = """
            EmailAddress.person = Person.id
            AND lower(email) LIKE %s || '%%'
            AND %s
            """ % (quote_like(text), base_query)

        email_match_query += extra_clause
        email_matches = Person.select(
            email_match_query, clauseTables=['EmailAddress'])

        # XXX Guilherme Salgado 2006-01-30 bug=30053:
        # We have to explicitly provide an orderBy here as a workaround
        return name_matches.union(
            email_matches, orderBy=['displayname', 'name'])


class ValidPersonVocabulary(ValidPersonOrTeamVocabulary):
    """The set of all valid, public persons who are not teams in Launchpad."""
    displayname = 'Select a Person'
    # The extra_clause for a valid person is that it not be a team, so
    # teamowner IS NULL.
    extra_clause = 'Person.teamowner IS NULL'
    # Search with empty string returns all valid people.
    allow_null_search = True
    # Cache table to use for checking validity.
    cache_table_name = 'ValidPersonCache'


class ValidTeamMemberVocabulary(ValidPersonOrTeamVocabulary):
    """The set of valid members of a given team.

    With the exception of all teams that have this team as a member and the
    team itself, all valid persons and teams are valid members.
    """

    def __init__(self, context):
        if not context:
            raise AssertionError('ValidTeamMemberVocabulary needs a context.')
        if ITeam.providedBy(context):
            self.team = context
        else:
            raise AssertionError(
                "ValidTeamMemberVocabulary's context must implement ITeam."
                "Got %s" % str(context))

        ValidPersonOrTeamVocabulary.__init__(self, context)
        self.extra_clause = """
            Person.id NOT IN (
                SELECT team FROM TeamParticipation
                WHERE person = %d
                ) AND Person.id != %d
            """ % (self.team.id, self.team.id)


class ValidTeamOwnerVocabulary(ValidPersonOrTeamVocabulary):
    """The set of Persons/Teams that can be owner of a team.

    With the exception of the team itself and all teams owned by that team,
    all valid persons and teams are valid owners for the team.
    """

    def __init__(self, context):
        if not context:
            raise AssertionError('ValidTeamOwnerVocabulary needs a context.')

        if IPerson.providedBy(context):
            self.extra_clause = """
                (person.teamowner != %d OR person.teamowner IS NULL) AND
                person.id != %d""" % (context.id, context.id)
        elif IPersonSet.providedBy(context):
            # The context is an IPersonSet, which means we're creating a new
            # team and thus we don't need any extra_clause --any valid person
            # or team can be the owner of a newly created team.
            pass
        else:
            raise AssertionError(
                "ValidTeamOwnerVocabulary's context must provide IPerson "
                "or IPersonSet.")
        ValidPersonOrTeamVocabulary.__init__(self, context)


class PersonActiveMembershipVocabulary:
    """All the teams the person is an active member of."""

    implements(IVocabularyTokenized)

    def __init__(self, context):
        assert IPerson.providedBy(context)
        self.context = context

    def _get_teams(self):
        """The teams that the vocabulary is built from."""
        return [membership.team for membership
                in self.context.myactivememberships
                if membership.team.visibility == PersonVisibility.PUBLIC]

    def __len__(self):
        """See `IVocabularyTokenized`."""
        return len(self._get_teams())

    def __iter__(self):
        """See `IVocabularyTokenized`."""
        return iter([self.getTerm(team) for team in self._get_teams()])

    def getTerm(self, team):
        """See `IVocabularyTokenized`."""
        if team not in self:
            raise LookupError(team)
        return SimpleTerm(team, team.name, team.displayname)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        for team in self._get_teams():
            if team.name == token:
                return self.getTerm(team)
        else:
            raise LookupError(token)

    def __contains__(self, obj):
        """See `IVocabularyTokenized`."""
        return obj in self._get_teams()


class ActiveMailingListVocabulary:
    """The set of all active mailing lists."""

    implements(IHugeVocabulary)

    displayname = 'Select an active mailing list.'

    def __init__(self, context):
        assert context is None, (
            'Unexpected context for ActiveMailingListVocabulary')

    def __iter__(self):
        """See `IIterableVocabulary`."""
        return iter(getUtility(IMailingListSet).active_lists)

    def __len__(self):
        """See `IIterableVocabulary`."""
        return getUtility(IMailingListSet).active_lists.count()

    def __contains__(self, team_list):
        """See `ISource`."""
        # Unlike other __contains__() implementations in this module, and
        # somewhat contrary to the interface definition, this method does not
        # return False when team_list is not an IMailingList.  No interface
        # check of the argument is done here.  Doing the interface check and
        # returning False when we get an unexpected type would be more
        # Pythonic, but we deliberately break that rule because it is
        # considered more helpful to generate an OOPS when the wrong type of
        # object is used in a containment test.  The __contains__() methods in
        # this module that type check their arguments is considered incorrect.
        # This also implies that .getTerm(), contrary to its interface
        # definition, will not always raise LookupError when the term isn't in
        # the vocabulary, because an exceptions from the containment test it
        # does will just be passed on up the call stack.
        return team_list.status == MailingListStatus.ACTIVE

    def toTerm(self, team_list):
        """Turn the team mailing list into a SimpleTerm."""
        return SimpleTerm(team_list, team_list.team.name,
                          team_list.team.displayname)

    def getTerm(self, team_list):
        """See `IBaseVocabulary`."""
        if team_list not in self:
            raise LookupError(team_list)
        return self.toTerm(team_list)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        # token should be the team name as a string.
        team_list = getUtility(IMailingListSet).get(token)
        if team_list is None:
            raise LookupError(token)
        return self.getTerm(team_list)

    def search(self, text=None):
        """Search for active mailing lists.

        :param text: The name of a mailing list, which can be a partial
            name.  This actually matches against the name of the team to which
            the mailing list is linked.  If None (the default), all active
            mailing lists are returned.
        :return: An iterator over the active mailing lists matching the query.
        """
        if text is None:
            return getUtility(IMailingListSet).active_lists
        # The mailing list name, such as it has one, is really the name of the
        # team to which it is linked.
        return MailingList.select("""
            MailingList.team = Person.id
            AND Person.fti @@ ftq(%s)
            AND Person.teamowner IS NOT NULL
            AND MailingList.status = %s
            """ % sqlvalues(text, MailingListStatus.ACTIVE),
            clauseTables=['Person'])

    def searchForTerms(self, query=None):
        """See `IHugeVocabulary`."""
        results = self.search(query)
        return CountableIterator(results.count(), results, self.toTerm)


def person_term(person):
    """Return a SimpleTerm for the `Person`."""
    return SimpleTerm(person, person.name, title=person.displayname)


def person_team_participations_vocabulary_factory(context):
    """Return a SimpleVocabulary containing the teams a person
    participate in.
    """
    assert context is not None
    person = IPerson(context)
    return SimpleVocabulary([
        person_term(team) for team in person.teams_participated_in])


class UserTeamsParticipationPlusSelfVocabulary(
    UserTeamsParticipationVocabulary):
    """A vocabulary containing the public teams that the logged
    in user participates in, along with the logged in user themselves.
    """

    def __iter__(self):
        logged_in_user = getUtility(ILaunchBag).user
        yield self.toTerm(logged_in_user)
        super_class = super(UserTeamsParticipationPlusSelfVocabulary, self)
        for person in super_class.__iter__():
            yield person

    def getTermByToken(self, token):
        logged_in_user = getUtility(ILaunchBag).user
        if logged_in_user.name == token:
            return self.getTerm(logged_in_user)
        super_class = super(UserTeamsParticipationPlusSelfVocabulary, self)
        return super_class.getTermByToken(token)


class ProductReleaseVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    displayname = 'Select a Product Release'
    _table = ProductRelease
    # XXX carlos Perello Marin 2005-05-16 bugs=687:
    # Sorting by version won't give the expected results, because it's just a
    # text field.  e.g. ["1.0", "2.0", "11.0"] would be sorted as ["1.0",
    # "11.0", "2.0"].
    _orderBy = [Product.q.name, ProductSeries.q.name, Milestone.q.name]
    _clauseTables = ['Product', 'ProductSeries']

    def toTerm(self, obj):
        productrelease = obj
        productseries = productrelease.productseries
        product = productseries.product

        # NB: We use '/' as the seperator because '-' is valid in
        # a product.name or productseries.name
        token = '%s/%s/%s' % (
                    product.name, productseries.name, productrelease.version)
        return SimpleTerm(
            obj.id, token, '%s %s %s' % (
                product.name, productseries.name, productrelease.version))

    def getTermByToken(self, token):
        try:
            productname, productseriesname, productreleaseversion = \
                token.split('/', 2)
        except ValueError:
            raise LookupError(token)

        obj = ProductRelease.selectOne(
            AND(ProductRelease.q.milestoneID == Milestone.q.id,
                Milestone.q.productseriesID == ProductSeries.q.id,
                ProductSeries.q.productID == Product.q.id,
                Product.q.name == productname,
                ProductSeries.q.name == productseriesname
                )
            )
        try:
            return self.toTerm(obj)
        except IndexError:
            raise LookupError(token)

    def search(self, query):
        """Return terms where query is a substring of the version or name"""
        if not query:
            return self.emptySelectResults()

        query = query.lower()
        objs = self._table.select(
            AND(
                Milestone.q.id == ProductRelease.q.milestoneID,
                ProductSeries.q.id == Milestone.q.productseriesID,
                Product.q.id == ProductSeries.q.productID,
                OR(
                    CONTAINSSTRING(Product.q.name, query),
                    CONTAINSSTRING(ProductSeries.q.name, query),
                    )
                ),
            orderBy=self._orderBy
            )

        return objs


class ProductSeriesVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    displayname = 'Select a Release Series'
    _table = ProductSeries
    _orderBy = [Product.q.name, ProductSeries.q.name]
    _clauseTables = ['Product']

    def toTerm(self, obj):
        # NB: We use '/' as the seperator because '-' is valid in
        # a product.name or productseries.name
        token = '%s/%s' % (obj.product.name, obj.name)
        return SimpleTerm(
            obj, token, '%s %s' % (obj.product.name, obj.name))

    def getTermByToken(self, token):
        try:
            productname, productseriesname = token.split('/', 1)
        except ValueError:
            raise LookupError(token)

        result = ProductSeries.selectOne('''
                    Product.id = ProductSeries.product AND
                    Product.name = %s AND
                    ProductSeries.name = %s
                    ''' % sqlvalues(productname, productseriesname),
                    clauseTables=['Product'])
        if result is not None:
            return self.toTerm(result)
        raise LookupError(token)

    def search(self, query):
        """Return terms where query is a substring of the name"""
        if not query:
            return self.emptySelectResults()

        query = query.lower()
        objs = self._table.select(
                AND(
                    Product.q.id == ProductSeries.q.productID,
                    OR(
                        CONTAINSSTRING(Product.q.name, query),
                        CONTAINSSTRING(ProductSeries.q.name, query)
                        )
                    ),
                orderBy=self._orderBy
                )
        return objs


class FilteredDistroSeriesVocabulary(SQLObjectVocabularyBase):
    """Describes the series of a particular distribution."""
    _table = DistroSeries
    _orderBy = 'version'

    def toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, '%s %s' % (obj.distribution.name, obj.name))

    def __iter__(self):
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        launchbag = getUtility(ILaunchBag)
        if launchbag.distribution:
            distribution = launchbag.distribution
            serieses = self._table.selectBy(
                distributionID=distribution.id, **kw)
            for series in sorted(serieses, key=attrgetter('sortkey')):
                yield self.toTerm(series)


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


class FilteredProductSeriesVocabulary(SQLObjectVocabularyBase):
    """Describes ProductSeries of a particular product."""
    _table = ProductSeries
    _orderBy = ['product', 'name']

    def toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, '%s %s' % (obj.product.name, obj.name))

    def __iter__(self):
        launchbag = getUtility(ILaunchBag)
        if launchbag.product is not None:
            for series in launchbag.product.serieses:
                yield self.toTerm(series)


class FutureSprintVocabulary(NamedSQLObjectVocabulary):
    """A vocab of all sprints that have not yet finished."""

    _table = Sprint

    def __iter__(self):
        future_sprints = Sprint.select("time_ends > 'NOW'")
        for sprint in future_sprints:
            yield(self.toTerm(sprint))


class MilestoneVocabulary(SQLObjectVocabularyBase):
    _table = Milestone
    _orderBy = None

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.displayname)

    @staticmethod
    def getMilestoneTarget(milestone_context):
        if IUpstreamBugTask.providedBy(milestone_context):
            target = milestone_context.product
        elif IDistroBugTask.providedBy(milestone_context):
            target = milestone_context.distribution
        elif IDistroSeriesBugTask.providedBy(milestone_context):
            target = milestone_context.distroseries
        elif IProductSeriesBugTask.providedBy(milestone_context):
            target = milestone_context.productseries
        elif IDistributionSourcePackage.providedBy(milestone_context):
            target = milestone_context.distribution
        elif ISourcePackage.providedBy(milestone_context):
            target = milestone_context.distroseries
        elif ISpecification.providedBy(milestone_context):
            target = milestone_context.target
        elif (IProject.providedBy(milestone_context) or
              IProduct.providedBy(milestone_context) or
              IProductSeries.providedBy(milestone_context) or
              IDistribution.providedBy(milestone_context) or
              IDistroSeries.providedBy(milestone_context)):
            target = milestone_context
        else:
            # We didn't find a context that can have milestones attached
            # to it.
            target = None
        return target

    @cachedproperty
    def visible_milestones(self):
        milestone_context = self.context
        target = MilestoneVocabulary.getMilestoneTarget(milestone_context)

        # XXX: Brad Bollenbach 2006-02-24: Listifying milestones is
        # evil, but we need to sort the milestones by a non-database
        # value, for the user to find the milestone they're looking
        # for (particularly when showing *all* milestones on the
        # person pages.)
        #
        # This fixes an urgent bug though, so I think this problem
        # should be revisited after we've unblocked users.
        if target is not None:
            if IProject.providedBy(target):
                milestones = shortlist(
                    (milestone for product in target.products
                     for milestone in product.milestones),
                    longest_expected=40)
            elif IProductSeries.providedBy(target):
                series_milestones = shortlist(target.milestones,
                                              longest_expected=40)
                product_milestones = shortlist(target.product.milestones,
                                               longest_expected=40)
                # Some milestones are associtaed with a product
                # and a product series; these should appear only
                # once.
                milestones = set(series_milestones + product_milestones)
            else:
                milestones = shortlist(
                    target.milestones, longest_expected=40)
        else:
            # We can't use context to reasonably filter the
            # milestones, so let's either just grab all of them,
            # or let's return an empty vocabulary.
            # Generally, returning all milestones is a bad idea: We
            # have at present (2009-04-08) nearly 2000 active milestones,
            # and nobody really wants to search through such a huge list
            # on a web page. This problem is fixed for an IPerson
            # context by browser.person.RelevantMilestonesMixin.
            # getMilestoneWidgetValues() which creates a "sane" milestone
            # set. We need to create the big vocabulary of all visible
            # milestones nevertheless, in order to allow the validation
            # of submitted milestone values.
            #
            # For other targets, like MaloneApplication, we return an empty
            # vocabulary.
            if IPerson.providedBy(self.context):
                milestones = shortlist(
                    getUtility(IMilestoneSet).getVisibleMilestones(),
                    longest_expected=40)
            else:
                milestones = []

        if (IBugTask.providedBy(milestone_context) and
            milestone_context.milestone is not None and
            milestone_context.milestone not in milestones):
            # Even if we inactivate a milestone, a bugtask might still be
            # linked to it. Include such milestones in the vocabulary to
            # ensure that the +editstatus page doesn't break.
            milestones.append(milestone_context.milestone)

        # Prefetch products and distributions for rendering
        # milestones: optimization to reduce the number of queries.
        product_ids = set(
            removeSecurityProxy(milestone).productID
            for milestone in milestones)
        distro_ids = set(
            removeSecurityProxy(milestone).distributionID
            for milestone in milestones)
        if len(product_ids) > 0:
            list(Product.select("id IN %s" % sqlvalues(product_ids)))
        if len(distro_ids) > 0:
            list(Distribution.select("id IN %s" % sqlvalues(distro_ids)))

        return sorted(milestones, key=attrgetter('displayname'))

    def __iter__(self):
        for milestone in self.visible_milestones:
            yield self.toTerm(milestone)

    def __contains__(self, obj):
        if IProjectMilestone.providedBy(obj):
            # Project milestones are pseudo content objects
            # which aren't really a part of this vocabulary,
            # but sometimes we want to pass them to fields
            # that rely on this vocabulary for validation
            # so we special-case them here just for that purpose.
            return obj.target.getMilestone(obj.name)
        else:
            return SQLObjectVocabularyBase.__contains__(self, obj)


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


class CommercialProjectsVocabulary(NamedSQLObjectVocabulary):
    """List all commercial projects.

    A commercial project is one that does not qualify for free hosting.  For
    normal users only commercial projects for which the user is the
    maintainer, or in the maintainers team, will be listed.  For users with
    launchpad.Commercial permission, all commercial projects are returned.
    """

    implements(IHugeVocabulary)

    _table = Product
    _orderBy = 'displayname'

    @property
    def displayname(self):
        return 'Select a commercial project'

    def _filter_projs(self, projects):
        """Filter the list of all projects to just the commercial ones."""
        return [
            project for project in sorted(projects,
                                          key=attrgetter('displayname'))
            if not project.qualifies_for_free_hosting
            ]

    def _doSearch(self, query=None):
        """Return terms where query is in the text of name
        or displayname, or matches the full text index.
        """
        user = self.context
        if user is None:
            return self.emptySelectResults()
        if check_permission('launchpad.Commercial', user):
            product_set = getUtility(IProductSet)
            projects = product_set.forReview(
                search_text=query, licenses=[License.OTHER_PROPRIETARY],
                active=True)
        else:
            projects = user.getOwnedProjects(match_name=query)
            projects = self._filter_projs(projects)
        return projects

    def toTerm(self, project):
        """Return the term for this object."""
        if project.commercial_subscription is None:
            sub_status = "(unsubscribed)"
        else:
            date_formatter = DateTimeFormatterAPI(
                project.commercial_subscription.date_expires)
            sub_status = "(expires %s)" % date_formatter.displaydate()
        return SimpleTerm(project,
                          project.name,
                          sub_status)

    def getTermByToken(self, token):
        """Return the term for the given token."""
        search_results = self._doSearch(token)
        for search_result in search_results:
            if search_result.name == token:
                return self.toTerm(search_result)
        raise LookupError(token)

    def searchForTerms(self, query=None):
        """See `SQLObjectVocabularyBase`."""
        results = self._doSearch(query)
        if type(results) is list:
            num = len(results)
        else:
            num = results.count()
        return CountableIterator(num, results, self.toTerm)

    def _commercial_projects(self):
        """Return the list of commercial project owned by this user."""
        return self._filter_projs(self._doSearch())

    def __iter__(self):
        """See `IVocabulary`."""
        for proj in self._commercial_projects():
            yield self.toTerm(proj)

    def __contains__(self, obj):
        """See `IVocabulary`."""
        return obj in self._filter_projs([obj])


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


class DistributionVocabulary(NamedSQLObjectVocabulary):

    _table = Distribution
    _orderBy = 'name'

    def getTermByToken(self, token):
        obj = Distribution.selectOne("name=%s" % sqlvalues(token))
        if obj is None:
            raise LookupError(token)
        else:
            return self.toTerm(obj)

    def search(self, query):
        """Return terms where query is a substring of the name"""
        if not query:
            return self.emptySelectResults()

        query = query.lower()
        like_query = "'%%' || %s || '%%'" % quote_like(query)
        fti_query = quote(query)
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        return self._table.select("name LIKE %s" % like_query, **kw)


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


class DistroSeriesVocabulary(NamedSQLObjectVocabulary):

    _table = DistroSeries
    _orderBy = ["Distribution.displayname", "-DistroSeries.date_created"]
    _clauseTables = ['Distribution']

    def __iter__(self):
        serieses = self._table.select(
            DistroSeries.q.distributionID==Distribution.q.id,
            orderBy=self._orderBy, clauseTables=self._clauseTables)
        for series in sorted(serieses, key=attrgetter('sortkey')):
            yield self.toTerm(series)

    def toTerm(self, obj):
        # NB: We use '/' as the separator because '-' is valid in
        # a distribution.name
        token = '%s/%s' % (obj.distribution.name, obj.name)
        title = "%s: %s" % (obj.distribution.displayname, obj.title)
        return SimpleTerm(obj, token, title)

    def getTermByToken(self, token):
        try:
            distroname, distroseriesname = token.split('/', 1)
        except ValueError:
            raise LookupError(token)

        obj = DistroSeries.selectOne('''
                    Distribution.id = DistroSeries.distribution AND
                    Distribution.name = %s AND
                    DistroSeries.name = %s
                    ''' % sqlvalues(distroname, distroseriesname),
                    clauseTables=['Distribution'])
        if obj is None:
            raise LookupError(token)
        else:
            return self.toTerm(obj)

    def search(self, query):
        """Return terms where query is a substring of the name."""
        if not query:
            return self.emptySelectResults()

        query = query.lower()
        objs = self._table.select(
                AND(
                    Distribution.q.id == DistroSeries.q.distributionID,
                    OR(
                        CONTAINSSTRING(Distribution.q.name, query),
                        CONTAINSSTRING(DistroSeries.q.name, query)
                        )
                    ),
                orderBy=self._orderBy
                )
        return objs


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


class PillarVocabularyBase(NamedSQLObjectHugeVocabulary):

    displayname = 'Needs to be overridden'
    _table = PillarName
    _orderBy = 'name'

    def toTerm(self, obj):
        if IPillarName.providedBy(obj):
            assert obj.active, 'Inactive object %s %d' % (
                    obj.__class__.__name__, obj.id
                    )
            obj = obj.pillar

        # It is a hack using the class name here, but it works
        # fine and avoids an ugly if statement.
        title = '%s (%s)' % (obj.title, obj.__class__.__name__)

        return SimpleTerm(obj, obj.name, title)

    def __contains__(self, obj):
        raise NotImplementedError


class DistributionOrProductVocabulary(PillarVocabularyBase):
    displayname = 'Select a project'
    _filter = """
        -- An active product/distro.
        ((active IS TRUE
         AND (product IS NOT NULL OR distribution IS NOT NULL)
        )
        OR
        -- Or an alias for an active product/distro.
        (alias_for IN (
            SELECT id FROM PillarName
            WHERE active IS TRUE AND
                (product IS NOT NULL OR distribution IS NOT NULL))
        ))
        """

    def __contains__(self, obj):
        if IProduct.providedBy(obj):
            # Only active products are in the vocabulary.
            return obj.active
        else:
            return IDistribution.providedBy(obj)


class DistributionOrProductOrProjectVocabulary(PillarVocabularyBase):
    displayname = 'Select a project'
    _filter = PillarName.q.active == True

    def __contains__(self, obj):
        if IProduct.providedBy(obj) or IProject.providedBy(obj):
            # Only active products and projects are in the vocabulary.
            return obj.active
        else:
            return IDistribution.providedBy(obj)


class FeaturedProjectVocabulary(DistributionOrProductOrProjectVocabulary):
    """Vocabulary of projects that are featured on the LP Home Page."""

    _filter = AND(PillarName.q.id == FeaturedProject.q.pillar_name,
                  PillarName.q.active == True)
    _clauseTables = ['FeaturedProject']

    def __contains__(self, obj):
        """See `IVocabulary`."""
        query = """PillarName.id=FeaturedProject.pillar_name
                   AND PillarName.name = %s""" % sqlvalues(obj.name)
        return PillarName.selectOne(
                   query, clauseTables=['FeaturedProject']) is not None


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
