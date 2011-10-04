# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Vocabularies for content objects.

Vocabularies that represent a set of content objects should be in this module.
Those vocabularies that are only used for providing a UI are better placed in
the browser code.

Note that you probably shouldn't be importing stuff from these modules, as it
is better to have your schema's fields look up the vocabularies by name. Some
of these vocabularies will only work if looked up by name, as they require
context to calculate the available options. Obtaining a vocabulary by name
also avoids circular import issues.

eg.

class IFoo(Interface):
    thingy = Choice(..., vocabulary='Thingies')

The binding of name -> class is done in the configure.zcml
"""

__metaclass__ = type

__all__ = [
    'ActiveMailingListVocabulary',
    'AdminMergeablePersonVocabulary',
    'AllUserTeamsParticipationVocabulary',
    'CommercialProjectsVocabulary',
    'DistributionOrProductOrProjectGroupVocabulary',
    'DistributionOrProductVocabulary',
    'DistributionSourcePackageVocabulary',
    'DistributionVocabulary',
    'DistroSeriesDerivationVocabulary',
    'DistroSeriesDifferencesVocabulary',
    'DistroSeriesVocabulary',
    'FeaturedProjectVocabulary',
    'FilteredDistroSeriesVocabulary',
    'FilteredProductSeriesVocabulary',
    'KarmaCategoryVocabulary',
    'MilestoneVocabulary',
    'NonMergedPeopleAndTeamsVocabulary',
    'person_team_participations_vocabulary_factory',
    'PersonAccountToMergeVocabulary',
    'PersonActiveMembershipVocabulary',
    'ProductReleaseVocabulary',
    'ProductSeriesVocabulary',
    'ProductVocabulary',
    'project_products_vocabulary_factory',
    'ProjectGroupVocabulary',
    'SourcePackageNameVocabulary',
    'UserTeamsParticipationPlusSelfVocabulary',
    'UserTeamsParticipationVocabulary',
    'ValidPersonOrTeamVocabulary',
    'ValidPersonVocabulary',
    'ValidTeamMemberVocabulary',
    'ValidTeamOwnerVocabulary',
    'ValidTeamVocabulary',
    ]


from operator import attrgetter

from lazr.restful.interfaces import IReference
from lazr.restful.utils import safe_hasattr
from sqlobject import (
    AND,
    CONTAINSSTRING,
    OR,
    )
from storm.expr import (
    Alias,
    And,
    Desc,
    Join,
    LeftJoin,
    Not,
    Or,
    Select,
    SQL,
    Union,
    With,
    )
from storm.info import ClassAlias
from storm.store import EmptyResultSet
from zope.component import getUtility
from zope.interface import implements
from zope.schema.interfaces import IVocabularyTokenized
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )
from zope.security.interfaces import Unauthorized
from zope.security.proxy import (
    isinstance as zisinstance,
    removeSecurityProxy,
    )

from canonical.database.sqlbase import (
    quote,
    quote_like,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.helpers import (
    ensure_unicode,
    shortlist,
    )
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    ILaunchBag,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.launchpad.webapp.publisher import nearest
from canonical.launchpad.webapp.vocabulary import (
    BatchedCountableIterator,
    CountableIterator,
    FilteredVocabularyBase,
    IHugeVocabulary,
    NamedSQLObjectHugeVocabulary,
    NamedSQLObjectVocabulary,
    SQLObjectVocabularyBase,
    VocabularyFilter,
    )
from lp.app.browser.tales import DateTimeFormatterAPI
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.blueprints.interfaces.specification import ISpecification
from lp.bugs.interfaces.bugtask import IBugTask
from lp.registry.interfaces.distribution import (
    IDistribution,
    IDistributionSet,
    )
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    )
from lp.registry.interfaces.mailinglist import (
    IMailingListSet,
    MailingListStatus,
    )
from lp.registry.interfaces.milestone import (
    IMilestoneSet,
    IProjectGroupMilestone,
    )
from lp.registry.interfaces.person import (
    CLOSED_TEAM_POLICY,
    IPerson,
    IPersonSet,
    ITeam,
    PersonVisibility,
    )
from lp.registry.interfaces.pillar import (
    IPillar,
    IPillarName,
    )
from lp.registry.interfaces.product import (
    IProduct,
    IProductSet,
    License,
    )
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.interfaces.sourcepackagename import ISourcePackageName
from lp.registry.model.distribution import Distribution
from lp.registry.model.distributionsourcepackage import (
    DistributionSourcePackageInDatabase,
    )
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.distroseriesdifference import DistroSeriesDifference
from lp.registry.model.distroseriesparent import DistroSeriesParent
from lp.registry.model.featuredproject import FeaturedProject
from lp.registry.model.karma import KarmaCategory
from lp.registry.model.mailinglist import MailingList
from lp.registry.model.milestone import Milestone
from lp.registry.model.person import (
    IrcID,
    Person,
    )
from lp.registry.model.pillar import PillarName
from lp.registry.model.product import Product
from lp.registry.model.productrelease import ProductRelease
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.projectgroup import ProjectGroup
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database import bulk
from lp.services.features import getFeatureFlag
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.model.distroarchseries import DistroArchSeries


class BasePersonVocabulary:
    """This is a base class used by all different Person Vocabularies."""

    _table = Person

    def __init__(self, context=None):
        super(BasePersonVocabulary, self).__init__(context)
        self.enhanced_picker_enabled = bool(
            getFeatureFlag('disclosure.picker_enhancements.enabled'))

    def toTerm(self, obj):
        """Return the term for this object."""
        try:
            return SimpleTerm(obj, obj.name, obj.displayname)
        except Unauthorized:
            return None

    def getTermByToken(self, token):
        """Return the term for the given token.

        If the token contains an '@', treat it like an email. Otherwise,
        treat it like a name.
        """
        token = ensure_unicode(token)
        if "@" in token:
            # This looks like an email token, so let's do an object
            # lookup based on that.
            email = IStore(EmailAddress).find(
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
            term = self.toTerm(person)
            if term is None:
                raise LookupError(token)
            return term


class KarmaCategoryVocabulary(NamedSQLObjectVocabulary):
    """All `IKarmaCategory` objects vocabulary."""
    _table = KarmaCategory
    _orderBy = 'name'


class ProductVocabulary(SQLObjectVocabularyBase):
    """All `IProduct` objects vocabulary."""
    implements(IHugeVocabulary)
    step_title = 'Search'

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
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        # Product names are always lowercase.
        token = token.lower()
        product = self._table.selectOneBy(name=token, active=True)
        if product is None:
            raise LookupError(token)
        return self.toTerm(product)

    def search(self, query, vocab_filter=None):
        """See `SQLObjectVocabularyBase`.

        Returns products where the product name, displayname, title,
        summary, or description contain the given query. Returns an empty list
        if query is None or an empty string.
        """
        if query:
            query = ensure_unicode(query).lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
            fti_query = quote(query)
            sql = "active = 't' AND (name LIKE %s OR fti @@ ftq(%s))" % (
                    like_query, fti_query)
            if getFeatureFlag('disclosure.picker_enhancements.enabled'):
                order_by = (
                    '(CASE name WHEN %s THEN 1 '
                    ' ELSE rank(fti, ftq(%s)) END) DESC, displayname, name'
                    % (fti_query, fti_query))
            else:
                order_by = self._orderBy
            return self._table.select(sql, orderBy=order_by, limit=100)
        return self.emptySelectResults()


class ProjectGroupVocabulary(SQLObjectVocabularyBase):
    """All `IProjectGroup` objects vocabulary."""
    implements(IHugeVocabulary)

    _table = ProjectGroup
    _orderBy = 'displayname'
    displayname = 'Select a project group'
    step_title = 'Search'

    def __contains__(self, obj):
        where = "active='t' and id=%d"
        if zisinstance(obj, SQLBase):
            project = self._table.selectOne(where % obj.id)
            return project is not None and project == obj
        else:
            project = self._table.selectOne(where % int(obj))
            return project is not None

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        project = self._table.selectOneBy(name=token, active=True)
        if project is None:
            raise LookupError(token)
        return self.toTerm(project)

    def search(self, query, vocab_filter=None):
        """See `SQLObjectVocabularyBase`.

        Returns projects where the project name, displayname, title,
        summary, or description contain the given query. Returns an empty list
        if query is None or an empty string.
        """
        if query:
            query = ensure_unicode(query).lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
            fti_query = quote(query)
            sql = "active = 't' AND (name LIKE %s OR fti @@ ftq(%s))" % (
                    like_query, fti_query)
            return self._table.select(sql)
        return self.emptySelectResults()


def project_products_vocabulary_factory(context):
    """Return a SimpleVocabulary containing the project's products."""
    assert context is not None
    project = IProjectGroup(context)
    return SimpleVocabulary([
        SimpleTerm(product, product.name, title=product.displayname)
        for product in project.products])


class UserTeamsParticipationVocabulary(SQLObjectVocabularyBase):
    """Describes the teams in which the current user participates."""
    _table = Person
    _orderBy = 'displayname'

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.name, obj.unique_displayname)

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
        """See `IVocabularyTokenized`."""
        launchbag = getUtility(ILaunchBag)
        if launchbag.user:
            user = launchbag.user
            for team in user.teams_participated_in:
                if team.name == token:
                    return self.getTerm(team)
        raise LookupError(token)


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
    step_title = 'Search'

    def __contains__(self, obj):
        return obj in self._select()

    def _select(self, text=""):
        """Return `IPerson` objects that match the text."""
        return getUtility(IPersonSet).find(text)

    def search(self, text, vocab_filter=None):
        """See `SQLObjectVocabularyBase`.

        Return people/teams whose fti or email address match :text.
        """
        if not text:
            return self.emptySelectResults()

        return self._select(ensure_unicode(text).lower())


class PersonAccountToMergeVocabulary(
        BasePersonVocabulary, SQLObjectVocabularyBase):
    """The set of all non-merged people with at least one email address.

    This vocabulary is a very specialized one, meant to be used only to choose
    accounts to merge. You *don't* want to use it.
    """
    implements(IHugeVocabulary)

    _orderBy = ['displayname']
    displayname = 'Select a Person to Merge'
    step_title = 'Search'
    must_have_email = True

    def __contains__(self, obj):
        return obj in self._select()

    def _select(self, text=""):
        """Return `IPerson` objects that match the text."""
        return getUtility(IPersonSet).findPerson(
            text, exclude_inactive_accounts=False,
            must_have_email=self.must_have_email)

    def search(self, text, vocab_filter=None):
        """See `SQLObjectVocabularyBase`.

        Return people whose fti or email address match :text.
        """
        if not text:
            return self.emptySelectResults()

        text = ensure_unicode(text).lower()
        return self._select(text)


class AdminMergeablePersonVocabulary(PersonAccountToMergeVocabulary):
    """The set of all non-merged people.

    This vocabulary is a very specialized one, meant to be used only for
    admins to choose accounts to merge. You *don't* want to use it.
    """
    must_have_email = False


class VocabularyFilterPerson(VocabularyFilter):
    # A filter returning just persons.

    def __new__(cls):
        return super(VocabularyFilter, cls).__new__(
            cls, 'PERSON', 'Person',
            'Display search results for people only')

    @property
    def filter_terms(self):
        return [Person.teamownerID == None]


class VocabularyFilterTeam(VocabularyFilter):
    # A filter returning just teams.

    def __new__(cls):
        return super(VocabularyFilter, cls).__new__(
            cls, 'TEAM', 'Team',
            'Display search results for teams only')

    @property
    def filter_terms(self):
        return [Person.teamownerID != None]


class ValidPersonOrTeamVocabulary(
        BasePersonVocabulary, SQLObjectVocabularyBase):
    """The set of valid, viewable Persons/Teams in Launchpad.

    A Person is considered valid if she has a preferred email address, and
    Person.merged is None. Teams have no restrictions at all, which means that
    all teams the user has the permission to view are considered valid.  A
    user can view private teams in which she is a member and any public team.

    This vocabulary is registered as ValidPersonOrTeam, ValidAssignee,
    ValidMaintainer and ValidOwner, because they have exactly the same
    requisites.
    """
    implements(IHugeVocabulary)

    displayname = 'Select a Person or Team'
    step_title = 'Search'
    # This is what subclasses must change if they want any extra filtering of
    # results.
    extra_clause = True

    # Subclasses should override this property to allow null searches to
    # return all results.  If false, an empty result set is returned.
    allow_null_search = False

    # Cache table to use for checking validity.
    cache_table_name = 'ValidPersonOrTeamCache'

    LIMIT = 100

    PERSON_FILTER = VocabularyFilterPerson()
    TEAM_FILTER = VocabularyFilterTeam()

    def __contains__(self, obj):
        return obj in self._doSearch()

    @cachedproperty
    def store(self):
        """The storm store."""
        return getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

    @cachedproperty
    def _karma_context_constraint(self):
        context = nearest(self.context, IPillar)
        if IProduct.providedBy(context):
            karma_context_column = 'product'
        elif IDistribution.providedBy(context):
            karma_context_column = 'distribution'
        elif IProjectGroup.providedBy(context):
            karma_context_column = 'project'
        else:
            return None
        return '%s = %d' % (karma_context_column, context.id)

    def _privateTeamQueryAndTables(self):
        """Return query tables for private teams.

        The teams are based on membership by the user.
        Returns a tuple of (query, tables).
        """
        tables = []
        logged_in_user = getUtility(ILaunchBag).user
        if logged_in_user is not None:
            celebrities = getUtility(ILaunchpadCelebrities)
            if logged_in_user.inTeam(celebrities.admin):
                # If the user is a LP admin we allow all private teams to be
                # visible.
                private_query = AND(
                    Not(Person.teamowner == None),
                    Person.visibility == PersonVisibility.PRIVATE)
            else:
                private_query = AND(
                    TeamParticipation.person == logged_in_user.id,
                    Not(Person.teamowner == None),
                    Person.visibility == PersonVisibility.PRIVATE)
                tables = [Join(TeamParticipation,
                               TeamParticipation.teamID == Person.id)]
        else:
            private_query = False
        return (private_query, tables)

    def _doSearch(self, text="", vocab_filter=None):
        """Return the people/teams whose fti or email address match :text:"""
        if self.enhanced_picker_enabled:
            return self._doSearchWithImprovedSorting(text, vocab_filter)
        else:
            return self._doSearchWithOriginalSorting(text, vocab_filter)

    def _doSearchWithOriginalSorting(self, text="", vocab_filter=None):
        private_query, private_tables = self._privateTeamQueryAndTables()
        exact_match = None
        extra_clauses = [self.extra_clause]
        if vocab_filter:
            extra_clauses.extend(vocab_filter.filter_terms)

        # Short circuit if there is no search text - all valid people and
        # teams have been requested. We still honour the vocab filter.
        if not text:
            tables = [
                Person,
                Join(self.cache_table_name,
                     SQL("%s.id = Person.id" % self.cache_table_name)),
                ]
            tables.extend(private_tables)
            result = self.store.using(*tables).find(
                Person,
                And(
                    Or(Person.visibility == PersonVisibility.PUBLIC,
                       private_query,
                       ),
                    Person.merged == None,
                    *extra_clauses
                    )
                )
        else:
            # Do a full search based on the text given.

            # The queries are broken up into several steps for efficiency.
            # The public person and team searches do not need to join with the
            # TeamParticipation table, which is very expensive.  The search
            # for private teams does need that table but the number of private
            # teams is very small so the cost is not great.

            # First search for public persons and teams that match the text.
            public_tables = [
                Person,
                LeftJoin(EmailAddress, EmailAddress.person == Person.id),
                ]

            # Create an inner query that will match public persons and teams
            # that have the search text in the fti, at the start of the email
            # address, or as their full IRC nickname.
            # Since we may be eliminating results with the limit to improve
            # performance, we sort by the rank, so that we will always get
            # the best results. The fti rank will be between 0 and 1.
            # Note we use lower() instead of the non-standard ILIKE because
            # ILIKE doesn't hit the indexes.
            # The '%%' is necessary because storm variable substitution
            # converts it to '%'.
            public_inner_textual_select = SQL("""
                SELECT id FROM (
                    SELECT Person.id, 100 AS rank
                    FROM Person
                    WHERE name = ?
                    UNION ALL
                    SELECT Person.id, rank(fti, ftq(?))
                    FROM Person
                    WHERE Person.fti @@ ftq(?)
                    UNION ALL
                    SELECT Person.id, 10 AS rank
                    FROM Person, IrcId
                    WHERE IrcId.person = Person.id
                        AND lower(IrcId.nickname) = ?
                    UNION ALL
                    SELECT Person.id, 1 AS rank
                    FROM Person, EmailAddress
                    WHERE EmailAddress.person = Person.id
                        AND lower(email) LIKE ? || '%%'
                        AND EmailAddress.status IN (?, ?)
                    ) AS public_subquery
                ORDER BY rank DESC
                LIMIT ?
                """, (text, text, text, text, text,
                      EmailAddressStatus.VALIDATED.value,
                      EmailAddressStatus.PREFERRED.value,
                      self.LIMIT))

            public_result = self.store.using(*public_tables).find(
                Person,
                And(
                    Person.id.is_in(public_inner_textual_select),
                    Person.visibility == PersonVisibility.PUBLIC,
                    Person.merged == None,
                    Or(  # A valid person-or-team is either a team...
                       # Note: 'Not' due to Bug 244768.
                       Not(Person.teamowner == None),
                       # Or a person who has a preferred email address.
                       EmailAddress.status == EmailAddressStatus.PREFERRED),
                    ))
            # The public query doesn't need to be ordered as it will be done
            # at the end.
            public_result.order_by()

            # Next search for the private teams.
            private_query, private_tables = self._privateTeamQueryAndTables()
            private_tables = [Person] + private_tables

            # Searching for private teams that match can be easier since we
            # are only interested in teams.  Teams can have email addresses
            # but we're electing to ignore them here.
            private_result = self.store.using(*private_tables).find(
                Person,
                And(
                    SQL('Person.fti @@ ftq(?)', [text]),
                    private_query,
                    )
                )

            private_result.order_by(SQL('rank(fti, ftq(?)) DESC', [text]))
            private_result.config(limit=self.LIMIT)

            combined_result = public_result.union(private_result)
            # Eliminate default ordering.
            combined_result.order_by()
            # XXX: BradCrittenden 2009-04-26 bug=217644: The use of Alias and
            # _get_select() is a work-around for .count() not working
            # with the 'distinct' option.
            subselect = Alias(combined_result._get_select(), 'Person')
            exact_match = (Person.name == text)
            result = self.store.using(subselect).find(
                (Person, exact_match),
                *extra_clauses)
        # XXX: BradCrittenden 2009-05-07 bug=373228: A bug in Storm prevents
        # setting the 'distinct' and 'limit' options in a single call to
        # .config().  The work-around is to split them up.  Note the limit has
        # to be after the call to 'order_by' for this work-around to be
        # effective.
        result.config(distinct=True)
        if exact_match is not None:
            # A DISTINCT requires that the sort parameters appear in the
            # select, but it will break the vocabulary if it returns a list of
            # tuples instead of a list of Person objects, so we create
            # another subselect to sort after the DISTINCT is done.
            distinct_subselect = Alias(result._get_select(), 'Person')
            result = self.store.using(distinct_subselect).find(Person)
            result.order_by(
                Desc(exact_match), Person.displayname, Person.name)
        else:
            result.order_by(Person.displayname, Person.name)
        result.config(limit=self.LIMIT)
        return result

    def _doSearchWithImprovedSorting(self, text="", vocab_filter=None):
        """Return the people/teams whose fti or email address match :text:"""

        private_query, private_tables = self._privateTeamQueryAndTables()
        extra_clauses = [self.extra_clause]
        if vocab_filter:
            extra_clauses.extend(vocab_filter.filter_terms)

        # Short circuit if there is no search text - all valid people and/or
        # teams have been requested. We still honour the vocab filter.
        if not text:
            tables = [
                Person,
                Join(self.cache_table_name,
                     SQL("%s.id = Person.id" % self.cache_table_name)),
                ]
            tables.extend(private_tables)
            result = self.store.using(*tables).find(
                Person,
                And(
                    Or(Person.visibility == PersonVisibility.PUBLIC,
                       private_query,
                       ),
                    Person.merged == None,
                    *extra_clauses
                    )
                )
            result.config(distinct=True)
            result.order_by(Person.displayname, Person.name)
        else:
            # Do a full search based on the text given.

            # The queries are broken up into several steps for efficiency.
            # The public person and team searches do not need to join with the
            # TeamParticipation table, which is very expensive.  The search
            # for private teams does need that table but the number of private
            # teams is very small so the cost is not great. However, if the
            # person is a logged in administrator, we don't need to join to
            # the TeamParticipation table and can construct a more efficient
            # query (since in this case we are searching all private teams).

            # Create a query that will match public persons and teams that
            # have the search text in the fti, at the start of their email
            # address, as their full IRC nickname, or at the start of their
            # displayname.
            # Since we may be eliminating results with the limit to improve
            # performance, we sort by the rank, so that we will always get
            # the best results. The fti rank will be between 0 and 1.
            # Note we use lower() instead of the non-standard ILIKE because
            # ILIKE doesn't hit the indexes.
            # The '%%' is necessary because storm variable substitution
            # converts it to '%'.

            # This is the SQL that will give us the IDs of the people we want
            # in the result.
            matching_person_sql = SQL("""
                SELECT id, MAX(rank) AS rank, false as is_private_team
                FROM (
                    SELECT Person.id,
                    (case
                        when person.name=? then 100
                        when person.name like ? || '%%' then 0.6
                        when lower(person.displayname) like ? || '%%' then 0.5
                        else rank(fti, ftq(?))
                    end) as rank
                    FROM Person
                    WHERE Person.name LIKE ? || '%%'
                    or lower(Person.displayname) LIKE ? || '%%'
                    or Person.fti @@ ftq(?)
                    UNION ALL
                    SELECT Person.id, 0.8 AS rank
                    FROM Person, IrcID
                    WHERE Person.id = IrcID.person
                        AND LOWER(IrcID.nickname) = LOWER(?)
                    UNION ALL
                    SELECT Person.id, 0.4 AS rank
                    FROM Person, EmailAddress
                    WHERE Person.id = EmailAddress.person
                        AND LOWER(EmailAddress.email) LIKE ? || '%%'
                        AND status IN (?, ?)
                ) AS person_match
                GROUP BY id, is_private_team
            """, (text, text, text, text, text, text, text, text, text,
                  EmailAddressStatus.VALIDATED.value,
                  EmailAddressStatus.PREFERRED.value))

            # Do we need to search for private teams.
            if private_tables:
                private_tables = [Person] + private_tables
                private_ranking_sql = SQL("""
                    (case
                        when person.name=? then 100
                        when person.name like ? || '%%' then 0.6
                        when lower(person.displayname) like ? || '%%' then 0.5
                        else rank(fti, ftq(?))
                    end) as rank
                """, (text, text, text, text))

                # Searching for private teams that match can be easier since
                # we are only interested in teams.  Teams can have email
                # addresses but we're electing to ignore them here.
                private_result_select = Select(
                    tables=private_tables,
                    columns=(Person.id, private_ranking_sql,
                                SQL("true as is_private_team")),
                    where=And(
                        SQL("""
                            Person.name LIKE ? || '%%'
                            OR lower(Person.displayname) LIKE ? || '%%'
                            OR Person.fti @@ ftq(?)
                            """, [text, text, text]),
                        private_query))
                matching_person_sql = Union(matching_person_sql,
                          private_result_select, all=True)

            # The tables for public persons and teams that match the text.
            public_tables = [
                SQL("MatchingPerson"),
                Person,
                LeftJoin(EmailAddress, EmailAddress.person == Person.id),
                ]

            # If private_tables is empty, we are searching for all private
            # teams. We can simply append the private query component to the
            # public query. Otherwise, for efficiency as stated earlier, we
            # need to do a separate query to join to the TeamParticipation
            # table.
            private_teams_query = private_query
            if private_tables:
                private_teams_query = SQL("is_private_team")

            # We just select the required ids since we will use
            # IPersonSet.getPrecachedPersonsFromIDs to load the results
            matching_with = With("MatchingPerson", matching_person_sql)
            result = self.store.with_(
                matching_with).using(*public_tables).find(
                Person,
                And(
                    SQL("Person.id = MatchingPerson.id"),
                    Or(
                        And(  # A public person or team
                            Person.visibility == PersonVisibility.PUBLIC,
                            Person.merged == None,
                            Or(  # A valid person-or-team is either a team...
                                # Note: 'Not' due to Bug 244768.
                                Not(Person.teamowner == None),
                                # Or a person who has preferred email address.
                                EmailAddress.status ==
                                    EmailAddressStatus.PREFERRED)),
                        # Or a private team
                        private_teams_query),
                    *extra_clauses),
                )
            # Better ranked matches go first.
            if (getFeatureFlag('disclosure.person_affiliation_rank.enabled')
                and self._karma_context_constraint):
                rank_order = SQL("""
                    rank * COALESCE(
                        (SELECT LOG(karmavalue) FROM KarmaCache
                         WHERE person = Person.id AND
                            %s
                            AND category IS NULL AND karmavalue > 10),
                        1) DESC""" % self._karma_context_constraint)
            else:
                rank_order = SQL("rank DESC")
            result.order_by(rank_order, Person.displayname, Person.name)
        result.config(limit=self.LIMIT)

        # We will be displaying the person's irc nick(s) and emails in the
        # description so we need to bulk load them for performance, otherwise
        # we get one query per person per attribute.
        def pre_iter_hook(rows):
            persons = set(obj for obj in rows)
            # The emails.
            emails = bulk.load_referencing(
                EmailAddress, persons, ['personID'])
            email_by_person = dict((email.personID, email)
                for email in emails
                if email.status == EmailAddressStatus.PREFERRED)

            for person in persons:
                cache = get_property_cache(person)
                cache.preferredemail = email_by_person.get(person.id, None)
                cache.ircnicknames = []

            # The irc nicks.
            nicks = bulk.load_referencing(IrcID, persons, ['personID'])
            for nick in nicks:
                get_property_cache(nick.person).ircnicknames.append(nick)

        return DecoratedResultSet(result, pre_iter_hook=pre_iter_hook)

    def search(self, text, vocab_filter=None):
        """Return people/teams whose fti or email address match :text:."""
        if not text:
            if self.allow_null_search:
                text = ''
            else:
                return self.emptySelectResults()

        text = ensure_unicode(text).lower()
        return self._doSearch(text=text, vocab_filter=vocab_filter)

    def searchForTerms(self, query=None, vocab_filter=None):
        """See `IHugeVocabulary`."""
        results = self.search(query, vocab_filter)
        return CountableIterator(results.count(), results, self.toTerm)

    def supportedFilters(self):
        """See `IHugeVocabulary`."""
        return [self.ALL_FILTER, self.PERSON_FILTER, self.TEAM_FILTER]


class ValidTeamVocabulary(ValidPersonOrTeamVocabulary):
    """The set of all valid, public teams in Launchpad."""

    displayname = 'Select a Team'

    # Because the base class does almost everything we need, we just need to
    # restrict the search results to those Persons who have a non-NULL
    # teamowner, i.e. a valid team.
    extra_clause = Not(Person.teamowner == None)
    # Search with empty string returns all teams.
    allow_null_search = True

    def _doSearch(self, text="", vocab_filter=None):
        """Return the teams whose fti, IRC, or email address match :text:"""

        private_query, private_tables = self._privateTeamQueryAndTables()
        base_query = And(
            Or(
                Person.visibility == PersonVisibility.PUBLIC,
                private_query,
                ),
            Person.merged == None
            )

        tables = [Person] + private_tables

        if not text:
            query = And(base_query,
                        Person.merged == None,
                        self.extra_clause)
            result = self.store.using(*tables).find(Person, query)
        else:
            if self.enhanced_picker_enabled:
                name_match_query = SQL("""
                    Person.name LIKE ? || '%%'
                    OR lower(Person.displayname) LIKE ? || '%%'
                    OR Person.fti @@ ftq(?)
                    """, [text, text, text]),
            else:
                name_match_query = SQL("Person.fti @@ ftq(%s)" % quote(text))

            email_storm_query = self.store.find(
                EmailAddress.personID,
                EmailAddress.email.lower().startswith(text))
            email_subquery = Alias(email_storm_query._get_select(),
                                   'EmailAddress')
            tables += [
                LeftJoin(email_subquery, EmailAddress.person == Person.id),
                ]

            result = self.store.using(*tables).find(
                Person,
                And(base_query,
                    self.extra_clause,
                    Or(name_match_query,
                       EmailAddress.person != None)))

        # To get the correct results we need to do distinct first, then order
        # by, then limit.
        result.config(distinct=True)
        result.order_by(Person.displayname, Person.name)
        result.config(limit=self.LIMIT)
        return result

    def supportedFilters(self):
        return []


class ValidPersonVocabulary(ValidPersonOrTeamVocabulary):
    """The set of all valid persons who are not teams in Launchpad."""
    displayname = 'Select a Person'
    # The extra_clause for a valid person is that it not be a team, so
    # teamowner IS NULL.
    extra_clause = 'Person.teamowner IS NULL'
    # Search with empty string returns all valid people.
    allow_null_search = True
    # Cache table to use for checking validity.
    cache_table_name = 'ValidPersonCache'

    def supportedFilters(self):
        return []


class TeamVocabularyMixin:
    """Common methods for team vocabularies."""

    displayname = 'Select a Team or Person'

    @property
    def is_closed_team(self):
        return self.team.subscriptionpolicy in CLOSED_TEAM_POLICY

    @property
    def step_title(self):
        """See `IHugeVocabulary`."""
        if self.is_closed_team:
            return (
                'Search for a restricted team, a moderated team, or a person')
        else:
            return 'Search'


class ValidTeamMemberVocabulary(TeamVocabularyMixin,
                                ValidPersonOrTeamVocabulary):
    """The set of valid members of a given team.

    With the exception of all teams that have this team as a member and the
    team itself, all valid persons and teams are valid members. Restricted
    and moderated teams cannot have open teams as members.
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

    @property
    def extra_clause(self):
        clause = SQL("""
            Person.id NOT IN (
                SELECT team FROM TeamParticipation
                WHERE person = %d
                )
            """ % self.team.id)
        if self.is_closed_team:
            clause = And(
                clause,
                Person.subscriptionpolicy.is_in(CLOSED_TEAM_POLICY))
        return clause


class ValidTeamOwnerVocabulary(TeamVocabularyMixin,
                               ValidPersonOrTeamVocabulary):
    """The set of Persons/Teams that can be owner of a team.

    With the exception of the team itself and all teams owned by that team,
    all valid persons and teams are valid owners for the team. Restricted
    and moderated teams cannot have open teams as members.
    """

    def __init__(self, context):
        if not context:
            raise AssertionError('ValidTeamOwnerVocabulary needs a context.')

        if IPerson.providedBy(context):
            self.team = context
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

    @property
    def extra_clause(self):
        clause = SQL("""
            (person.teamowner != %d OR person.teamowner IS NULL) AND
            person.id != %d""" % (self.team.id, self.team.id))
        if self.is_closed_team:
            clause = And(
                clause,
                Person.subscriptionpolicy.is_in(CLOSED_TEAM_POLICY))
        return clause


class AllUserTeamsParticipationVocabulary(ValidTeamVocabulary):
    """The set of teams where the current user is a member.

    Other than UserTeamsParticipationVocabulary, this vocabulary includes
    private teams.
    """

    displayname = 'Select a Team of which you are a member'

    def __init__(self, context):
        super(AllUserTeamsParticipationVocabulary, self).__init__(context)
        user = getUtility(ILaunchBag).user
        if user is None:
            self.extra_clause = False
        else:
            self.extra_clause = AND(
                super(AllUserTeamsParticipationVocabulary, self).extra_clause,
                TeamParticipation.person == user.id,
                TeamParticipation.team == Person.id)


class PersonActiveMembershipVocabulary:
    """All the teams the person is an active member of."""

    implements(IVocabularyTokenized)

    def __init__(self, context):
        assert IPerson.providedBy(context)
        self.context = context

    def _get_teams(self):
        """The teams that the vocabulary is built from."""
        return [membership.team for membership
                in self.context.team_memberships
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


class ActiveMailingListVocabulary(FilteredVocabularyBase):
    """The set of all active mailing lists."""

    implements(IHugeVocabulary)

    displayname = 'Select an active mailing list.'
    step_title = 'Search'

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
        """See `IVocabulary`.

        Turn the team mailing list into a SimpleTerm.
        """
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

    def search(self, text=None, vocab_filter=None):
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

    def searchForTerms(self, query=None, vocab_filter=None):
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
    """    """All `IProduct` objects vocabulary."""

    def __iter__(self):
        logged_in_user = getUtility(ILaunchBag).user
        yield self.toTerm(logged_in_user)
        super_class = super(UserTeamsParticipationPlusSelfVocabulary, self)
        for person in super_class.__iter__():
            yield person

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        logged_in_user = getUtility(ILaunchBag).user
        if logged_in_user.name == token:
            return self.getTerm(logged_in_user)
        super_class = super(UserTeamsParticipationPlusSelfVocabulary, self)
        return super_class.getTermByToken(token)


class UserTeamsParticipationPlusSelfSimpleDisplayVocabulary(
    UserTeamsParticipationPlusSelfVocabulary):
    """Like UserTeamsParticipationPlusSelfVocabulary but the term title is
    the person.displayname rather than unique_displayname.

    This vocab is used for pickers which append the Launchpad id to the
    displayname. If we use the original UserTeamsParticipationPlusSelf vocab,
    the Launchpad id is displayed twice.
    """

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.name, obj.displayname)


class ProductReleaseVocabulary(SQLObjectVocabularyBase):
    """All `IProductRelease` objects vocabulary."""
    implements(IHugeVocabulary)

    displayname = 'Select a Product Release'
    step_title = 'Search'
    _table = ProductRelease
    # XXX carlos Perello Marin 2005-05-16 bugs=687:
    # Sorting by version won't give the expected results, because it's just a
    # text field.  e.g. ["1.0", "2.0", "11.0"] would be sorted as ["1.0",
    # "11.0", "2.0"].
    _orderBy = [Product.q.name, ProductSeries.q.name, Milestone.q.name]
    _clauseTables = ['Product', 'ProductSeries']

    def toTerm(self, obj):
        """See `IVocabulary`."""
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
        """See `IVocabularyTokenized`."""
        try:
            productname, productseriesname, dummy = token.split('/', 2)
        except ValueError:
            raise LookupError(token)

        obj = ProductRelease.selectOne(
            AND(ProductRelease.q.milestoneID == Milestone.q.id,
                Milestone.q.productseriesID == ProductSeries.q.id,
                ProductSeries.q.productID == Product.q.id,
                Product.q.name == productname,
                ProductSeries.q.name == productseriesname))
        try:
            return self.toTerm(obj)
        except IndexError:
            raise LookupError(token)

    def search(self, query, vocab_filter=None):
        """Return terms where query is a substring of the version or name"""
        if not query:
            return self.emptySelectResults()

        query = ensure_unicode(query).lower()
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
    """All `IProductSeries` objects vocabulary."""
    implements(IHugeVocabulary)

    displayname = 'Select a Release Series'
    step_title = 'Search'
    _table = ProductSeries
    _order_by = [Product.name, ProductSeries.name]
    _clauseTables = ['Product']

    def toTerm(self, obj):
        """See `IVocabulary`."""
        # NB: We use '/' as the seperator because '-' is valid in
        # a product.name or productseries.name
        token = '%s/%s' % (obj.product.name, obj.name)
        return SimpleTerm(
            obj, token, '%s %s' % (obj.product.name, obj.name))

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        try:
            productname, productseriesname = token.split('/', 1)
        except ValueError:
            raise LookupError(token)

        result = IStore(self._table).find(
            self._table,
            ProductSeries.product == Product.id,
            Product.name == productname,
            ProductSeries.name == productseriesname).one()
        if result is not None:
            return self.toTerm(result)
        raise LookupError(token)

    def search(self, query, vocab_filter=None):
        """Return terms where query is a substring of the name."""
        if not query:
            return self.emptySelectResults()

        query = ensure_unicode(query).lower().strip('/')
        # If there is a slash splitting the product and productseries
        # names, they must both match. If there is no slash, we don't
        # know whether it is matching the product or the productseries
        # so we search both for the same string.
        if '/' in query:
            product_query, series_query = query.split('/', 1)
            substring_search = And(
                CONTAINSSTRING(Product.name, product_query),
                CONTAINSSTRING(ProductSeries.name, series_query))
        else:
            substring_search = Or(
                CONTAINSSTRING(Product.name, query),
                CONTAINSSTRING(ProductSeries.name, query))

        result = IStore(self._table).find(
            self._table,
            Product.id == ProductSeries.productID,
            substring_search)
        result = result.order_by(self._order_by)
        return result


class FilteredDistroSeriesVocabulary(SQLObjectVocabularyBase):
    """Describes the series of a particular distribution."""
    _table = DistroSeries
    _orderBy = 'version'

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(
            obj, obj.id, '%s %s' % (obj.distribution.name, obj.name))

    def __iter__(self):
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        launchbag = getUtility(ILaunchBag)
        if launchbag.distribution:
            distribution = launchbag.distribution
            series = self._table.selectBy(
                distributionID=distribution.id, **kw)
            for series in sorted(series, key=attrgetter('sortkey')):
                yield self.toTerm(series)


class FilteredProductSeriesVocabulary(SQLObjectVocabularyBase):
    """Describes ProductSeries of a particular product."""
    _table = ProductSeries
    _orderBy = ['product', 'name']

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(
            obj, obj.id, '%s %s' % (obj.product.name, obj.name))

    def __iter__(self):
        launchbag = getUtility(ILaunchBag)
        if launchbag.product is not None:
            for series in launchbag.product.series:
                yield self.toTerm(series)


class MilestoneVocabulary(SQLObjectVocabularyBase):
    """The milestones for a target."""
    _table = Milestone
    _orderBy = None

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.id, obj.displayname)

    @staticmethod
    def getMilestoneTarget(milestone_context):
        """Return the milestone target."""
        if IBugTask.providedBy(milestone_context):
            bug_target = milestone_context.target
            if IProduct.providedBy(bug_target):
                target = milestone_context.product
            elif IProductSeries.providedBy(bug_target):
                target = milestone_context.productseries.product
            elif (IDistribution.providedBy(bug_target) or
                  IDistributionSourcePackage.providedBy(bug_target)):
                target = milestone_context.distribution
            elif (IDistroSeries.providedBy(bug_target) or
                  ISourcePackage.providedBy(bug_target)):
                target = milestone_context.distroseries
        elif IDistributionSourcePackage.providedBy(milestone_context):
            target = milestone_context.distribution
        elif ISourcePackage.providedBy(milestone_context):
            target = milestone_context.distroseries
        elif ISpecification.providedBy(milestone_context):
            target = milestone_context.target
        elif IProductSeries.providedBy(milestone_context):
            # Show all the milestones of the product for a product series.
            target = milestone_context.product
        elif (IProjectGroup.providedBy(milestone_context) or
              IProduct.providedBy(milestone_context) or
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
        """Return the active milestones."""
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
            if IProjectGroup.providedBy(target):
                milestones_source = target.product_milestones
            else:
                milestones_source = target.milestones
            milestones = shortlist(milestones_source, longest_expected=40)
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
        product_ids.discard(None)
        distro_ids = set(
            removeSecurityProxy(milestone).distributionID
            for milestone in milestones)
        distro_ids.discard(None)
        if len(product_ids) > 0:
            list(Product.select("id IN %s" % sqlvalues(product_ids)))
        if len(distro_ids) > 0:
            list(Distribution.select("id IN %s" % sqlvalues(distro_ids)))

        return sorted(milestones, key=attrgetter('displayname'))

    def __iter__(self):
        for milestone in self.visible_milestones:
            yield self.toTerm(milestone)

    def __len__(self):
        return len(self.visible_milestones)

    def __contains__(self, obj):
        if IProjectGroupMilestone.providedBy(obj):
            # ProjectGroup milestones are pseudo content objects
            # which aren't really a part of this vocabulary,
            # but sometimes we want to pass them to fields
            # that rely on this vocabulary for validation
            # so we special-case them here just for that purpose.
            return obj.target.getMilestone(obj.name)
        else:
            return SQLObjectVocabularyBase.__contains__(self, obj)


class CommercialProjectsVocabulary(NamedSQLObjectVocabulary):
    """List all commercial projects.

    A commercial project is one that does not qualify for free hosting.  For
    normal users only commercial projects for which the user is the
    maintainer, or in the maintainers team, will be listed.  For users with
    launchpad.Moderate permission, all commercial projects are returned.
    """

    implements(IHugeVocabulary)

    _table = Product
    _orderBy = 'displayname'
    step_title = 'Search'

    @property
    def displayname(self):
        """The vocabulary's display nane."""
        return 'Select a commercial project'

    def _filter_projs(self, projects):
        """Filter the list of all projects to just the commercial ones."""
        return [
            project for project in sorted(projects,
                                          key=attrgetter('displayname'))
            if not project.qualifies_for_free_hosting]

    def _doSearch(self, query=None):
        """Return terms where query is in the text of name
        or displayname, or matches the full text index.
        """
        user = self.context
        if user is None:
            return self.emptySelectResults()
        product_set = getUtility(IProductSet)
        if check_permission('launchpad.Moderate', product_set):
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
                          '%s %s' % (project.title, sub_status))

    def getTermByToken(self, token):
        """Return the term for the given token."""
        search_results = self._doSearch(token)
        for search_result in search_results:
            if search_result.name == token:
                return self.toTerm(search_result)
        raise LookupError(token)

    def searchForTerms(self, query=None, vocab_filter=None):
        """See `SQLObjectVocabularyBase`."""
        results = self._doSearch(query)
        if type(results) is list:
            num = len(results)
        else:
            num = results.count()
        return CountableIterator(num, results, self.toTerm)

    def _commercial_projects(self):
        """Return the list of commercial projects owned by this user."""
        return self._filter_projs(self._doSearch())

    def __iter__(self):
        """See `IVocabulary`."""
        for proj in self._commercial_projects():
            yield self.toTerm(proj)

    def __contains__(self, obj):
        """See `IVocabulary`."""
        return obj in self._filter_projs([obj])


class DistributionVocabulary(NamedSQLObjectVocabulary):
    """All `IDistribution` objects vocabulary."""
    _table = Distribution
    _orderBy = 'name'

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        obj = Distribution.selectOne("name=%s" % sqlvalues(token))
        if obj is None:
            raise LookupError(token)
        else:
            return self.toTerm(obj)

    def search(self, query, vocab_filter=None):
        """Return terms where query is a substring of the name"""
        if not query:
            return self.emptySelectResults()

        query = query.lower()
        like_query = "'%%' || %s || '%%'" % quote_like(query)
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        return self._table.select("name LIKE %s" % like_query, **kw)


class DistroSeriesVocabulary(NamedSQLObjectVocabulary):
    """All `IDistroSeries` objects vocabulary."""
    _table = DistroSeries
    _orderBy = ["Distribution.displayname", "-DistroSeries.date_created"]
    _clauseTables = ['Distribution']

    def __iter__(self):
        series = self._table.select(
            DistroSeries.q.distributionID == Distribution.q.id,
            orderBy=self._orderBy, clauseTables=self._clauseTables)
        for series in sorted(series, key=attrgetter('sortkey')):
            yield self.toTerm(series)

    @staticmethod
    def toTerm(obj):
        """See `IVocabulary`."""
        # NB: We use '/' as the separator because '-' is valid in
        # a distribution.name
        token = '%s/%s' % (obj.distribution.name, obj.name)
        title = "%s: %s" % (obj.distribution.displayname, obj.title)
        return SimpleTerm(obj, token, title)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
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

    def search(self, query, vocab_filter=None):
        """Return terms where query is a substring of the name."""
        if not query:
            return self.emptySelectResults()

        query = ensure_unicode(query).lower()
        objs = self._table.select(
                AND(
                    Distribution.q.id == DistroSeries.q.distributionID,
                    OR(
                        CONTAINSSTRING(Distribution.q.name, query),
                        CONTAINSSTRING(DistroSeries.q.name, query))),
                    orderBy=self._orderBy)
        return objs


class DistroSeriesDerivationVocabulary(FilteredVocabularyBase):
    """A vocabulary source for series to derive from.

    Once a distribution has a series that has derived from a series in another
    distribution, all other derived series must also derive from a series in
    the same distribution.

    A distribution can have non-derived series. Any of these can be changed to
    derived at a later date, but as soon as this happens, the above rule
    applies.

    Also, a series must have architectures setup in LP to be a potential
    parent.

    It is permissible for a distribution to have both derived and non-derived
    series at the same time.
    """

    implements(IHugeVocabulary)

    displayname = "Add a parent series"
    step_title = 'Search'

    def __init__(self, context):
        """Create a new vocabulary for the context.

        :param context: It should adaptable to `IDistroSeries`.
        """
        assert IDistroSeries.providedBy(context)
        self.distribution = context.distribution

    def __len__(self):
        """See `IIterableVocabulary`."""
        return self.searchParents().count()

    def __iter__(self):
        """See `IIterableVocabulary`."""
        for series in self.searchParents():
            yield self.toTerm(series)

    def __contains__(self, value):
        """See `IVocabulary`."""
        if not IDistroSeries.providedBy(value):
            return False
        return value.id in [parent.id for parent in self.searchParents()]

    def getTerm(self, value):
        """See `IVocabulary`."""
        if value not in self:
            raise LookupError(value)
        return self.toTerm(value)

    def terms_by_token(self):
        """Mapping of terms by token."""
        return dict((term.token, term) for term in self.terms)

    def getTermByToken(self, token):
        try:
            return self.terms_by_token[token]
        except KeyError:
            raise LookupError(token)

    def toTerm(self, series):
        """Return the term for a parent series."""
        title = "%s: %s" % (series.distribution.displayname, series.title)
        return SimpleTerm(series, series.id, title)

    def searchForTerms(self, query=None, vocab_filter=None):
        """See `IHugeVocabulary`."""
        results = self.searchParents(query)
        return CountableIterator(len(results), results, self.toTerm)

    @cachedproperty
    def terms(self):
        return self.searchParents()

    def find_terms(self, *where):
        """Return a `tuple` of terms matching the given criteria.

        The terms are returned in order. The `Distribution`s related to those
        terms are preloaded at the same time.
        """
        query = IStore(DistroSeries).find(
            (DistroSeries, Distribution),
            DistroSeries.distribution == Distribution.id,
            *where)
        query = query.order_by(
            Distribution.displayname,
            Desc(DistroSeries.date_created)).config(distinct=True)
        return [series for (series, distribution) in query]

    def searchParents(self, query=None):
        """See `IHugeVocabulary`."""
        parent = ClassAlias(DistroSeries, "parent")
        child = ClassAlias(DistroSeries, "child")
        where = []
        if query is not None:
            term = '%' + query.lower() + '%'
            search = Or(
                    DistroSeries.title.lower().like(term),
                    DistroSeries.description.lower().like(term),
                    DistroSeries.summary.lower().like(term))
            where.append(search)
        parent_distributions = list(IStore(DistroSeries).find(
            parent.distributionID, And(
                parent.distributionID != self.distribution.id,
                child.distributionID == self.distribution.id,
                child.id == DistroSeriesParent.derived_series_id,
                parent.id == DistroSeriesParent.parent_series_id)))
        if parent_distributions != []:
            where.append(
                DistroSeries.distributionID.is_in(parent_distributions))
            return self.find_terms(where)
        else:
            # Select only the series with architectures setup in LP.
            where.append(
                DistroSeries.id == DistroArchSeries.distroseriesID)
            where.append(
                DistroSeries.distribution != self.distribution)
            return self.find_terms(where)


class DistroSeriesDifferencesVocabulary(FilteredVocabularyBase):
    """A vocabulary source for differences relating to a series.

    Specifically, all `DistroSeriesDifference`s relating to a derived series.
    """

    implements(IHugeVocabulary)

    displayname = "Choose a difference"
    step_title = 'Search'

    def __init__(self, context):
        """Create a new vocabulary for the context.

        :type context: `IDistroSeries`.
        """
        assert IDistroSeries.providedBy(context)
        self.distroseries = context

    def __len__(self):
        """See `IIterableVocabulary`."""
        return self.searchForDifferences().count()

    def __iter__(self):
        """See `IIterableVocabulary`."""
        for difference in self.searchForDifferences():
            yield self.toTerm(difference)

    def __contains__(self, value):
        """See `IVocabulary`."""
        return (
            IDistroSeriesDifference.providedBy(value) and
            value.derived_series == self.distroseries)

    def getTerm(self, value):
        """See `IVocabulary`."""
        if value not in self:
            raise LookupError(value)
        return self.toTerm(value)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        if not token.isdigit():
            raise LookupError(token)
        difference = IStore(DistroSeriesDifference).get(
            DistroSeriesDifference, int(token))
        if difference is None:
            raise LookupError(token)
        elif difference.derived_series != self.distroseries:
            raise LookupError(token)
        else:
            return self.toTerm(difference)

    @staticmethod
    def toTerm(dsd):
        """Return the term for a `DistroSeriesDifference`."""
        return SimpleTerm(dsd, dsd.id)

    def searchForTerms(self, query=None, vocab_filter=None):
        """See `IHugeVocabulary`."""
        results = self.searchForDifferences()
        return CountableIterator(results.count(), results, self.toTerm)

    def searchForDifferences(self):
        """The set of `DistroSeriesDifference`s related to the context.

        :return: `IResultSet` yielding `IDistroSeriesDifference`.
        """
        return DistroSeriesDifference.getForDistroSeries(self.distroseries)


class VocabularyFilterProject(VocabularyFilter):
    # A filter returning just projects.

    def __new__(cls):
        return super(VocabularyFilter, cls).__new__(
            cls, 'PROJECT', 'Project',
            'Display search results associated with projects')

    @property
    def filter_terms(self):
        return [PillarName.product != None]


class VocabularyFilterProjectGroup(VocabularyFilter):
    # A filter returning just project groups.

    def __new__(cls):
        return super(VocabularyFilter, cls).__new__(
            cls, 'PROJECTGROUP', 'Project Group',
            'Display search results associated with project groups')

    @property
    def filter_terms(self):
        return [PillarName.project != None]


class VocabularyFilterDistribution(VocabularyFilter):
    # A filter returning just distros.

    def __new__(cls):
        return super(VocabularyFilter, cls).__new__(
            cls, 'DISTRO', 'Distribution',
            'Display search results associated with distributions')

    @property
    def filter_terms(self):
        return [PillarName.distribution != None]


class PillarVocabularyBase(NamedSQLObjectHugeVocabulary):
    """Active `IPillar` objects vocabulary."""
    displayname = 'Needs to be overridden'
    _table = PillarName
    _limit = 100

    PROJECT_FILTER = VocabularyFilterProject()
    PROJECTGROUP_FILTER = VocabularyFilterProjectGroup()
    DISTRO_FILTER = VocabularyFilterDistribution()

    def supportedFilters(self):
        return [self.ALL_FILTER]

    def toTerm(self, obj):
        """See `IVocabulary`."""
        if type(obj) == int:
            return self.toTerm(PillarName.get(obj))
        if IPillarName.providedBy(obj):
            assert obj.active, 'Inactive object %s %d' % (
                    obj.__class__.__name__, obj.id)
            obj = obj.pillar

        enhanced = bool(getFeatureFlag(
            'disclosure.target_picker_enhancements.enabled'))
        if enhanced:
            title = '%s' % obj.title
        else:
            title = '%s (%s)' % (obj.title, obj.pillar_category)
        return SimpleTerm(obj, obj.name, title)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        # Pillar names are always lowercase.
        return super(PillarVocabularyBase, self).getTermByToken(
            token.lower())

    def __contains__(self, obj):
        raise NotImplementedError

    def searchForTerms(self, query=None, vocab_filter=None):
        if not query:
            return self.emptySelectResults()
        query = ensure_unicode(query).lower()
        store = IStore(PillarName)
        equal_clauses = [PillarName.name == query]
        like_clauses = [
            PillarName.name != query, PillarName.name.contains_string(query)]
        if self._filter:
            equal_clauses.extend(self._filter)
            like_clauses.extend(self._filter)
        if vocab_filter:
            equal_clauses.extend(vocab_filter.filter_terms)
            like_clauses.extend(vocab_filter.filter_terms)
        ranked_results = store.execute(
            Union(
                Select(
                    (PillarName.id, PillarName.name, SQL('100 AS rank')),
                    tables=[PillarName],
                    where=And(*equal_clauses)),
                Select(
                    (PillarName.id, PillarName.name, SQL('50 AS rank')),
                    tables=[PillarName],
                    where=And(*like_clauses)),
                limit=self._limit, order_by=(
                    Desc(SQL('rank')), PillarName.name), all=True))
        results = [row[0] for row in list(ranked_results)]
        return self.iterator(len(results), results, self.toTerm)


class DistributionOrProductVocabulary(PillarVocabularyBase):
    """Active `IDistribution` or `IProduct` objects vocabulary."""
    displayname = 'Select a project'
    _filter = [PillarName.project == None, PillarName.active == True]

    def __contains__(self, obj):
        if IProduct.providedBy(obj):
            # Only active products are in the vocabulary.
            return obj.active
        else:
            return IDistribution.providedBy(obj)

    def supportedFilters(self):
        return [
            self.ALL_FILTER,
            self.PROJECT_FILTER,
            self.DISTRO_FILTER]


class DistributionOrProductOrProjectGroupVocabulary(PillarVocabularyBase):
    """Active `IProduct`, `IProjectGroup` or `IDistribution` vocabulary."""
    displayname = 'Select a project'
    _filter = [PillarName.active == True]

    def __contains__(self, obj):
        if IProduct.providedBy(obj) or IProjectGroup.providedBy(obj):
            # Only active products and projects are in the vocabulary.
            return obj.active
        else:
            return IDistribution.providedBy(obj)

    def supportedFilters(self):
        return [
            self.ALL_FILTER,
            self.PROJECT_FILTER,
            self.PROJECTGROUP_FILTER,
            self.DISTRO_FILTER]


class FeaturedProjectVocabulary(
                               DistributionOrProductOrProjectGroupVocabulary):
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


class SourcePackageNameIterator(BatchedCountableIterator):
    """A custom iterator for SourcePackageNameVocabulary.

    Used to iterate over vocabulary items and provide full
    descriptions.

    Note that the reason we use special iterators is to ensure that we
    only do the search for descriptions across source package names that
    we actually are attempting to list, taking advantage of the
    resultset slicing that BatchNavigator does.
    """

    def getTermsWithDescriptions(self, results):
        return [SimpleTerm(obj, obj.name, obj.name) for obj in results]


class SourcePackageNameVocabulary(NamedSQLObjectHugeVocabulary):
    """A vocabulary that lists source package names."""
    displayname = 'Select a source package'
    _table = SourcePackageName
    _orderBy = 'name'
    iterator = SourcePackageNameIterator

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        # package names are always lowercase.
        return super(SourcePackageNameVocabulary, self).getTermByToken(
            token.lower())


class DistributionSourcePackageVocabulary(FilteredVocabularyBase):

    implements(IHugeVocabulary)
    displayname = 'Select a package'
    step_title = 'Search by name or distro/name'
    LIMIT = 60

    def __init__(self, context):
        self.context = context
        # Avoid circular import issues.
        from lp.answers.interfaces.question import IQuestion
        if IReference.providedBy(context):
            target = context.context.target
        elif IBugTask.providedBy(context) or IQuestion.providedBy(context):
            target = context.target
        else:
            target = context
        try:
            self.distribution = IDistribution(target)
        except TypeError:
            self.distribution = None
        if IDistributionSourcePackage.providedBy(target):
            self.dsp = target
        else:
            self.dsp = None

    def __contains__(self, spn_or_dsp):
        if spn_or_dsp == self.dsp:
            # Historic values are always valid. The DSP used to
            # initialize the vocabulary is always included.
            return True
        try:
            self.toTerm(spn_or_dsp)
            return True
        except LookupError:
            return False

    def __iter__(self):
        pass

    def __len__(self):
        pass

    def getDistributionAndPackageName(self, text):
        "Return the distribution and package name from the parsed text."
        # Match the toTerm() format, but also use it to select a distribution.
        distribution = None
        if '/' in text:
            distro_name, text = text.split('/', 1)
            distribution = getUtility(IDistributionSet).getByName(distro_name)
        if distribution is None:
            distribution = self.distribution
        return distribution, text

    def toTerm(self, spn_or_dsp, distribution=None):
        """See `IVocabulary`."""
        dsp = None
        if IDistributionSourcePackage.providedBy(spn_or_dsp):
            dsp = spn_or_dsp
            distribution = spn_or_dsp.distribution
        elif (not ISourcePackageName.providedBy(spn_or_dsp) and
            safe_hasattr(spn_or_dsp, 'distribution')
            and safe_hasattr(spn_or_dsp, 'sourcepackagename')):
            # We use the hasattr checks rather than adaption because the
            # DistributionSourcePackageInDatabase object is a little bit
            # broken, and does not provide any interface.
            distribution = spn_or_dsp.distribution
            dsp = distribution.getSourcePackage(spn_or_dsp.sourcepackagename)
        else:
            distribution = distribution or self.distribution
            if distribution is not None and spn_or_dsp is not None:
                dsp = distribution.getSourcePackage(spn_or_dsp)
        if dsp is not None and (dsp == self.dsp or dsp.is_official):
            token = '%s/%s' % (dsp.distribution.name, dsp.name)
            summary = '%s (%s)' % (token, dsp.name)
            return SimpleTerm(dsp, token, summary)
        raise LookupError(distribution, spn_or_dsp)

    def getTerm(self, spn_or_dsp):
        """See `IBaseVocabulary`."""
        return self.toTerm(spn_or_dsp)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        distribution, package_name = self.getDistributionAndPackageName(token)
        return self.toTerm(package_name, distribution)

    def searchForTerms(self, query=None, vocab_filter=None):
        """See `IHugeVocabulary`."""
        if not query:
            return EmptyResultSet()
        distribution, query = self.getDistributionAndPackageName(query)
        if distribution is None:
            # This could failover to ubuntu, but that is non-obvious. The
            # Python widget must set the default distribution and the JS
            # widget must encourage the <distro>/<package> search format.
            return EmptyResultSet()
        search_term = unicode(query)
        store = IStore(DistributionSourcePackageInDatabase)
        # Construct the searchable text that could live in the DSP table.
        # Limit the results to ensure the user could see all the batches.
        # Rank only what is returned: exact source name, exact binary
        # name, partial source name, and lastly partial binary name.
        searchable_dsp = SQL("""
            SELECT dsp.id, dsps.name, dsps.binpkgnames, rank
            FROM DistributionSourcePackage dsp
                JOIN (
                SELECT DISTINCT ON (dspc.sourcepackagename)
                    dspc.sourcepackagename, dspc.name, dspc.binpkgnames,
                    CASE WHEN dspc.name = ? THEN 100
                        WHEN dspc.binpkgnames SIMILAR TO
                            '(^| )' || ? || '( |$)' THEN 75
                        WHEN dspc.name SIMILAR TO
                            '(^|.*-)' || ? || '(-|$)' THEN 50
                        WHEN dspc.binpkgnames SIMILAR TO
                            '(^|.*-)' || ? || '(-| |$)' THEN 25
                        ELSE 1
                        END AS rank
                FROM DistributionSourcePackageCache dspc
                    JOIN Archive a ON dspc.archive = a.id AND a.purpose IN (
                        ?, ?)
                WHERE
                    dspc.name like '%%' || ? || '%%'
                    OR dspc.binpkgnames like '%%' || ? || '%%'
                LIMIT ?
                ) dsps ON dsp.sourcepackagename = dsps.sourcepackagename
            WHERE
                dsp.distribution = ?
            ORDER BY rank DESC
            """, (search_term, search_term, search_term, search_term,
                  ArchivePurpose.PRIMARY.value, ArchivePurpose.PARTNER.value,
                  search_term, search_term, self.LIMIT, distribution.id))
        matching_with = With('SearchableDSP', searchable_dsp)
        # It might be possible to return the source name and binary names to
        # reduce the work of the picker adapter.
        dsps = store.with_(matching_with).using(
            SQL('SearchableDSP'), DistributionSourcePackageInDatabase).find(
            DistributionSourcePackageInDatabase,
            SQL('DistributionSourcePackage.id = SearchableDSP.id'))
        return CountableIterator(dsps.count(), dsps, self.toTerm)
