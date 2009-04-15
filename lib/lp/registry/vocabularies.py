# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
"""Vocabularies for content objects.

Here should vocabularies that represent a set of conent objects be placed.
Vocabularies that are used only for providing a UI are better placed in
the browser code.

Note that you probably shouldn't be importing stuff from these
modules, as it is better to have your Schemas fields look up the vocabularies
by name. Some of these vocabularies will only work if looked up by name,
as they require context to calculare the available options. It also
avoids circular import issues.

eg.

class IFoo(Interface):
    thingy = Choice(..., vocabulary='Thingies')

The binding of name -> class is done in the configure.zcml
"""

__metaclass__ = type

__all__ = [
    'ActiveMailingListVocabulary',
    'CommercialProjectsVocabulary',
    'DistributionOrProductOrProjectVocabulary',
    'DistributionOrProductVocabulary',
    'DistributionVocabulary',
    'DistroSeriesVocabulary',
    'FeaturedProjectVocabulary',
    'FilteredDistroSeriesVocabulary',
    'FilteredProductSeriesVocabulary',
    'KarmaCategoryVocabulary',
    'MilestoneVocabulary',
    'NonMergedPeopleAndTeamsVocabulary',
    'PersonAccountToMergeVocabulary',
    'PersonActiveMembershipVocabulary',
    'ProductReleaseVocabulary',
    'ProductSeriesVocabulary',
    'ProductVocabulary',
    'ProjectVocabulary',
    'UserTeamsParticipationVocabulary',
    'UserTeamsParticipationPlusSelfVocabulary',
    'ValidPersonOrTeamVocabulary',
    'ValidPersonVocabulary',
    'ValidTeamMemberVocabulary',
    'ValidTeamOwnerVocabulary',
    'ValidTeamVocabulary',
    'person_team_participations_vocabulary_factory',
    'project_products_vocabulary_factory',
    ]


from operator import attrgetter

from sqlobject import AND, CONTAINSSTRING, OR

from storm.expr import LeftJoin, SQL, And, Or, Not

from zope.component import getUtility
from zope.interface import implements
from zope.schema.interfaces import IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.security.proxy import isinstance as zisinstance
from zope.security.proxy import removeSecurityProxy

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.database import (
    Account, Distribution, DistroSeries, EmailAddress, FeaturedProject,
    KarmaCategory, MailingList, Milestone, Person, PillarName, Product,
    ProductRelease, ProductSeries, Project)
from canonical.database.sqlbase import SQLBase, quote_like, quote, sqlvalues
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import IStore
from canonical.launchpad.interfaces.bugtask import (
    IBugTask, IDistroBugTask, IDistroSeriesBugTask, IProductSeriesBugTask,
    IUpstreamBugTask)
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.specification import ISpecification
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import (
    ILaunchBag, IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.launchpad.webapp.tales import DateTimeFormatterAPI
from canonical.launchpad.webapp.vocabulary import (
    CountableIterator, IHugeVocabulary, NamedSQLObjectHugeVocabulary,
    NamedSQLObjectVocabulary, SQLObjectVocabularyBase)

from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.mailinglist import (
    IMailingListSet, MailingListStatus)
from lp.registry.interfaces.milestone import IMilestoneSet, IProjectMilestone
from lp.registry.interfaces.person import (
    IPerson, IPersonSet, ITeam, PersonVisibility)
from lp.registry.interfaces.pillar import IPillarName
from lp.registry.interfaces.product import IProduct, IProductSet, License
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.project import IProject
from lp.registry.interfaces.sourcepackage import ISourcePackage


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


class KarmaCategoryVocabulary(NamedSQLObjectVocabulary):
    """All `IKarmaCategory` objects vocabulary."""
    _table = KarmaCategory
    _orderBy = 'name'


# XXX kiko 2007-01-18: any reason why this can't be an
# NamedSQLObjectHugeVocabulary?
class ProductVocabulary(SQLObjectVocabularyBase):
    """All `IProduct` objects vocabulary."""
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
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        product = self._table.selectOneBy(name=token, active=True)
        if product is None:
            raise LookupError(token)
        return self.toTerm(product)

    def search(self, query):
        """See `SQLObjectVocabularyBase`.

        Returns products where the product name, displayname, title,
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
    """All `IProject` objects vocabulary."""
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
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        project = self._table.selectOneBy(name=token, active=True)
        if project is None:
            raise LookupError(token)
        return self.toTerm(project)

    def search(self, query):
        """See `SQLObjectVocabularyBase`.

        Returns projects where the project name, displayname, title,
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
        """See `IVocabulary`."""
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

    def __contains__(self, obj):
        return obj in self._select()

    def _select(self, text=""):
        """Return `IPerson` objects that match the text."""
        return getUtility(IPersonSet).find(text)

    def search(self, text):
        """See `SQLObjectVocabularyBase`.

        Return people/teams whose fti or email address match :text.
        """
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
        """Return `IPerson` objects that match the text."""
        return getUtility(IPersonSet).findPerson(
            text, exclude_inactive_accounts=False, must_have_email=True)

    def search(self, text):
        """See `SQLObjectVocabularyBase`.

        Return people whose fti or email address match :text.
        """
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
        """See `SQLObjectVocabularyBase`.

        Return people/teams whose fti or email address match :text:.
        """
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


class ProductReleaseVocabulary(SQLObjectVocabularyBase):
    """All `IProductRelease` objects vocabulary."""
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
    """All `IProductSeries` objects vocabulary."""
    implements(IHugeVocabulary)

    displayname = 'Select a Release Series'
    _table = ProductSeries
    _orderBy = [Product.q.name, ProductSeries.q.name]
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
            serieses = self._table.selectBy(
                distributionID=distribution.id, **kw)
            for series in sorted(serieses, key=attrgetter('sortkey')):
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
            for series in launchbag.product.serieses:
                yield self.toTerm(series)


class MilestoneVocabulary(SQLObjectVocabularyBase):
    """All or some `IMilestone` objects vocabulary."""
    _table = Milestone
    _orderBy = None

    def toTerm(self, obj):
        """See `IVocabulary`."""
        return SimpleTerm(obj, obj.id, obj.displayname)

    @staticmethod
    def getMilestoneTarget(milestone_context):
        """Return the pillar or series that owns the milestone."""
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
        """All visible milestones."""
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
        """The vocabulary's display nane."""
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


class DistroSeriesVocabulary(NamedSQLObjectVocabulary):
    """All `IDistroSeries` objects vocabulary."""
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


class PillarVocabularyBase(NamedSQLObjectHugeVocabulary):
    """Active `IPillar` objects vocabulary."""
    displayname = 'Needs to be overridden'
    _table = PillarName
    _orderBy = 'name'

    def toTerm(self, obj):
        """See `IVocabulary`."""
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
    """Active `IProduct` or `IDistribution` objects vocabulary."""
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
    """Active `IProduct`, `IProject` or `IDistribution` objects vocabulary."""
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

