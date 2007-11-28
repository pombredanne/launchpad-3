# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Vocabularies pulling stuff from the database.

You probably don't want to use these classes directly - see the
docstring in __init__.py for details.
"""

__metaclass__ = type

__all__ = [
    'ActiveMailingListVocabulary',
    'BountyVocabulary',
    'BranchVocabulary',
    'BugNominatableSeriesesVocabulary',
    'BugVocabulary',
    'BugTrackerVocabulary',
    'BugWatchVocabulary',
    'ComponentVocabulary',
    'CountryNameVocabulary',
    'DistributionVocabulary',
    'DistributionOrProductVocabulary',
    'DistributionOrProductOrProjectVocabulary',
    'DistributionUsingMaloneVocabulary',
    'DistroSeriesVocabulary',
    'FAQVocabulary',
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
    'PackageReleaseVocabulary',
    'PersonAccountToMergeVocabulary',
    'PersonActiveMembershipVocabulary',
    'person_team_participations_vocabulary_factory',
    'ProcessorVocabulary',
    'ProcessorFamilyVocabulary',
    'ProductReleaseVocabulary',
    'ProductSeriesVocabulary',
    'ProductVocabulary',
    'ProjectVocabulary',
    'project_products_vocabulary_factory',
    'project_products_using_malone_vocabulary_factory',
    'SpecificationVocabulary',
    'SpecificationDependenciesVocabulary',
    'SpecificationDepCandidatesVocabulary',
    'SprintVocabulary',
    'TranslatableLanguageVocabulary',
    'TranslationGroupVocabulary',
    'TranslationMessageVocabulary',
    'UserTeamsParticipationVocabulary',
    'ValidPersonOrTeamVocabulary',
    'ValidTeamVocabulary',
    'ValidTeamMemberVocabulary',
    'ValidTeamOwnerVocabulary',
    ]

import cgi
from operator import attrgetter

from sqlobject import AND, CONTAINSSTRING, OR, SQLObjectNotFound
from zope.component import getUtility
from zope.interface import implements
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.security.proxy import isinstance as zisinstance

from canonical.launchpad.database import (
    Branch, BranchSet, Bounty, Bug, BugTracker, BugWatch, Component, Country,
    Distribution, DistroArchSeries, DistroSeries, KarmaCategory, Language,
    LanguagePack, MailingList, Milestone, Person, PillarName, Processor,
    ProcessorFamily, Product, ProductRelease, ProductSeries, Project,
    SourcePackageRelease, Specification, Sprint, TranslationGroup,
    TranslationMessage)
from canonical.database.sqlbase import SQLBase, quote_like, quote, sqlvalues
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
    DistroSeriesStatus, EmailAddressStatus, IBugTask, IDistribution,
    IDistributionSourcePackage, IDistroBugTask, IDistroSeries,
    IDistroSeriesBugTask, IEmailAddressSet, IFAQ, IFAQTarget, ILanguage,
    ILaunchBag, IMailingList, IMailingListSet, IMilestoneSet, IPerson,
    IPersonSet, IPillarName, IProduct, IProject, ISourcePackage,
    ISpecification, ITeam, IUpstreamBugTask, LanguagePackType,
    MailingListStatus)
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
            email = getUtility(IEmailAddressSet).getByEmail(token)
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


class BranchVocabulary(SQLObjectVocabularyBase):
    """A vocabulary for searching branches.

    If the context is a product or the launchbag contains a product,
    then the search results are limited to branches associated with
    that product.
    """

    implements(IHugeVocabulary)

    _table = Branch
    _orderBy = 'name'
    displayname = 'Select a Branch'

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.unique_name, obj.displayname)

    def getTermByToken(self, token):
        branch_set = BranchSet()
        branch = branch_set.getByUniqueName(token)
        # fall back to interpreting the token as a branch URL
        if branch is None:
            url = token.rstrip('/')
            branch = branch_set.getByUrl(url)
        if branch is None:
            raise LookupError(token)
        return self.toTerm(branch)

    def search(self, query):
        """Return terms where query is a subtring of the name or URL."""
        launch_bag = getUtility(ILaunchBag)
        branch_set = BranchSet()
        logged_in_user = launch_bag.user
        if not query:
            query = branch_set._generateBranchClause(
                query='', visible_by_user=logged_in_user)
            return Branch.select(query)

        quoted_query = quote_like(query)
        sql_query = ("""
            (Branch.name LIKE '%%' || %s || '%%' OR
             Branch.url LIKE '%%' || %s || '%%')
            """
            % (quoted_query, quoted_query))

        # If the context is a product or we have a product in the
        # LaunchBag, narrow the search appropriately.
        if IProduct.providedBy(self.context):
            product = self.context
        else:
            product = launch_bag.product
        if product is not None:
            sql_query = sql_query + (" AND Branch.product = %s" % product.id)

        sql_query = branch_set._generateBranchClause(
            sql_query, visible_by_user=logged_in_user)
        return Branch.select(sql_query, orderBy=self._orderBy)


class BugVocabulary(SQLObjectVocabularyBase):

    _table = Bug
    _orderBy = 'id'


class BountyVocabulary(SQLObjectVocabularyBase):

    _table = Bounty
    # XXX kiko 2006-02-20: no _orderBy?


class BugTrackerVocabulary(SQLObjectVocabularyBase):

    _table = BugTracker
    _orderBy = 'title'


class FAQVocabulary:
    """Vocabulary containing all the FAQs in an `IFAQTarget`."""

    implements(IHugeVocabulary)

    displayname = 'Select a FAQ'

    def __init__(self, context):
        """Create a new vocabulary for the context.

        :param context: It should adaptable to `IFAQTarget`.
        """
        self.context = IFAQTarget(context)

    def __len__(self):
        """See `IIterableVocabulary`."""
        return self.context.searchFAQs().count()

    def __iter__(self):
        """See `IIterableVocabulary`."""
        for faq in self.context.searchFAQs():
            yield self.toTerm(faq)

    def __contains__(self, value):
        """See `IVocabulary`."""
        if not IFAQ.providedBy(value):
            return False
        return self.context.getFAQ(value.id) is not None

    def getTerm(self, value):
        """See `IVocabulary`."""
        if value not in self:
            raise LookupError(value)
        return self.toTerm(value)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        try:
            faq_id = int(token)
        except ValueError:
            raise LookupError(token)
        faq = self.context.getFAQ(token)
        if faq is None:
            raise LookupError(token)
        return self.toTerm(faq)

    def toTerm(self, faq):
        """Return the term for a FAQ."""
        return SimpleTerm(faq, faq.id, faq.title)

    def searchForTerms(self, query=None):
        """See `IHugeVocabulary`."""
        results = self.context.findSimilarFAQs(query)
        return CountableIterator(results.count(), results, self.toTerm)


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
            text, exclude_inactive_accounts=False)

    def search(self, text):
        """Return people whose fti or email address match :text."""
        if not text:
            return self.emptySelectResults()

        text = text.lower()
        return self._select(text)


class ValidPersonOrTeamVocabulary(
        BasePersonVocabulary, SQLObjectVocabularyBase):
    """The set of valid Persons/Teams in Launchpad.

    A Person is considered valid if he has a preferred email address,
    a password set and Person.merged is None. Teams have no restrictions
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

    def __contains__(self, obj):
        return obj in self._doSearch()

    def _doSearch(self, text=""):
        """Return the people/teams whose fti or email address match :text:"""
        if self.extra_clause:
            extra_clause = " AND %s" % self.extra_clause
        else:
            extra_clause = ""

        if not text:
            query = 'Person.id = ValidPersonOrTeamCache.id' + extra_clause
            return Person.select(
                query, clauseTables=['ValidPersonOrTeamCache'])

        name_match_query = """
            Person.id = ValidPersonOrTeamCache.id
            AND Person.fti @@ ftq(%s)
            """ % quote(text)
        name_match_query += extra_clause
        name_matches = Person.select(
            name_match_query, clauseTables=['ValidPersonOrTeamCache'])

        # Note that we must use lower(email) LIKE rather than ILIKE
        # as ILIKE no longer appears to be hitting the index under PG8.0
        email_match_query = """
            EmailAddress.person = Person.id
            AND EmailAddress.person = ValidPersonOrTeamCache.id
            AND EmailAddress.status IN %s
            AND lower(email) LIKE %s || '%%'
            """ % (sqlvalues(EmailAddressStatus.VALIDATED,
                             EmailAddressStatus.PREFERRED),
                   quote_like(text))
        email_match_query += extra_clause
        email_matches = Person.select(
            email_match_query,
            clauseTables=['ValidPersonOrTeamCache', 'EmailAddress'])

        ircid_match_query = """
            IRCId.person = Person.id
            AND IRCId.person = ValidPersonOrTeamCache.id
            AND lower(IRCId.nickname) = %s
            """ % quote(text)
        ircid_match_query += extra_clause
        ircid_matches = Person.select(
            ircid_match_query,
            clauseTables=['ValidPersonOrTeamCache', 'IRCId'])

        # XXX Guilherme Salgado 2006-01-30 bug=30053:
        # We have to explicitly provide an orderBy here as a workaround
        return name_matches.union(ircid_matches).union(
            email_matches, orderBy=['displayname', 'name'])

    def search(self, text):
        """Return people/teams whose fti or email address match :text:."""
        if not text:
            return self.emptySelectResults()

        text = text.lower()
        return self._doSearch(text=text)


class ValidTeamVocabulary(ValidPersonOrTeamVocabulary):
    """The set of all valid teams in Launchpad."""

    displayname = 'Select a Team'

    # Because the base class does almost everything we need, we just need to
    # restrict the search results to those Persons who have a non-NULL
    # teamowner, i.e. a valid team.
    extra_clause = 'Person.teamowner IS NOT NULL'

    def search(self, text):
        """Return all teams that match :text:.

        Unlike ValidPersonOrTeamVocabulary, providing an empty string for text
        does not return the empty result set.  Instead, it returns all teams.
        """
        if not text:
            text = ''
        return self._doSearch(text=text)


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

        if ITeam.providedBy(context):
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
                "ValidTeamOwnerVocabulary's context must provide ITeam "
                "or IPersonSet.")
        ValidPersonOrTeamVocabulary.__init__(self, context)


class PersonActiveMembershipVocabulary:
    """All the teams the person is an active member of."""

    implements(IVocabulary, IVocabularyTokenized)

    def __init__(self, context):
        assert IPerson.providedBy(context)
        self.context = context

    def __len__(self):
        return self.context.myactivememberships.count()

    def __iter__(self):
        return iter(
            [self.getTerm(membership.team)
             for membership in self.context.myactivememberships])

    def getTerm(self, team):
        if team not in self:
            raise LookupError(team)
        return SimpleTerm(team, team.name, team.displayname)

    def __contains__(self, obj):
        if not ITeam.providedBy(obj):
            return False
        member_teams = [
            membership.team for membership in self.context.myactivememberships
            ]
        return obj in member_teams

    def getQuery(self):
        return None

    def getTermByToken(self, token):
        for membership in self.context.myactivememberships:
            if membership.team.name == token:
                return self.getTerm(membership.team)
        else:
            raise LookupError(token)


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


def person_team_participations_vocabulary_factory(context):
    """Return a SimpleVocabulary containing the teams a person
    participate in.
    """
    assert context is not None
    person = IPerson(context)
    return SimpleVocabulary([
        SimpleTerm(team, team.name, title=team.displayname)
        for team in person.teams_participated_in])


class ProductReleaseVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    displayname = 'Select a Product Release'
    _table = ProductRelease
    # XXX carlos Perello Marin 2005-05-16 bugs=687:
    # Sorting by version won't give the expected results, because it's just a
    # text field.  e.g. ["1.0", "2.0", "11.0"] would be sorted as ["1.0",
    # "11.0", "2.0"].
    _orderBy = [Product.q.name, ProductSeries.q.name,
                ProductRelease.q.version]
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
            AND(ProductRelease.q.productseriesID == ProductSeries.q.id,
                ProductSeries.q.productID == Product.q.id,
                Product.q.name == productname,
                ProductSeries.q.name == productseriesname,
                ProductRelease.q.version == productreleaseversion
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
                ProductSeries.q.id == ProductRelease.q.productseriesID,
                Product.q.id == ProductSeries.q.productID,
                OR(
                    CONTAINSSTRING(Product.q.name, query),
                    CONTAINSSTRING(ProductSeries.q.name, query),
                    CONTAINSSTRING(ProductRelease.q.version, query)
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

    def __iter__(self):
        target = None

        milestone_context = self.context

        if IUpstreamBugTask.providedBy(milestone_context):
            target = milestone_context.product
        elif IDistroBugTask.providedBy(milestone_context):
            target = milestone_context.distribution
        elif IDistroSeriesBugTask.providedBy(milestone_context):
            target = milestone_context.distroseries
        elif IDistributionSourcePackage.providedBy(milestone_context):
            target = milestone_context.distribution
        elif ISourcePackage.providedBy(milestone_context):
            target = milestone_context.distroseries
        elif ISpecification.providedBy(milestone_context):
            target = milestone_context.target
        elif (IProject.providedBy(milestone_context) or
              IProduct.providedBy(milestone_context) or
              IDistribution.providedBy(milestone_context) or
              IDistroSeries.providedBy(milestone_context)):
            target = milestone_context
        else:
            # We didn't find a context that can have milestones attached
            # to it.
            target = None

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
                     for milestone in product.all_milestones),
                    longest_expected=40)
            else:
                milestones = shortlist(
                    target.all_milestones, longest_expected=40)
        else:
            # We can't use context to reasonably filter the
            # milestones, so let's just grab all of them.
            milestones = shortlist(
                getUtility(IMilestoneSet), longest_expected=40)

        visible_milestones = [
            milestone for milestone in milestones if milestone.visible]
        if (IBugTask.providedBy(milestone_context) and
            milestone_context.milestone is not None and
            milestone_context.milestone not in visible_milestones):
            # Even if we inactivate a milestone, a bugtask might still be
            # linked to it. Include such milestones in the vocabulary to
            # ensure that the +editstatus page doesn't break.
            visible_milestones.append(milestone_context.milestone)

        for ms in sorted(visible_milestones, key=attrgetter('displayname')):
            yield self.toTerm(ms)


class SpecificationVocabulary(NamedSQLObjectVocabulary):
    """List specifications for the current product or distribution in
    ILaunchBag, EXCEPT for the current spec in LaunchBag if one exists.
    """

    _table = Specification
    _orderBy = 'title'

    def __iter__(self):
        launchbag = getUtility(ILaunchBag)
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
        return self._filter_specs(self.context.target.specifications())

    def __iter__(self):
        return (self.toTerm(spec) for spec in self._all_specs())

    def __contains__(self, obj):
        return obj in self._all_specs()

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
        return SimpleTerm(
            watch, watch.id, '%s <a href="%s">#%s</a>' % (
                cgi.escape(watch.bugtracker.title), watch.url,
                cgi.escape(watch.remotebug)))


class PackageReleaseVocabulary(SQLObjectVocabularyBase):
    _table = SourcePackageRelease
    _orderBy = 'id'

    def toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.name + " " + obj.version)


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
            if obj.product is not None:
                obj = obj.product
            elif obj.distribution is not None:
                obj = obj.distribution
            elif obj.project is not None:
                obj = obj.project
            else:
                raise AssertionError('Broken PillarName')

        # It is a hack using the class name here, but it works
        # fine and avoids an ugly if statement.
        title = '%s (%s)' % (obj.title, obj.__class__.__name__)

        return SimpleTerm(obj, obj.name, title)

    def __contains__(self, obj):
        raise NotImplementedError


class DistributionOrProductVocabulary(PillarVocabularyBase):
    displayname = 'Select a project'
    _filter = AND(OR(
            PillarName.q.distributionID != None,
            PillarName.q.productID != None
            ), PillarName.q.active == True)

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

