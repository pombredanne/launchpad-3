# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementations of `IGitCollection`."""

__metaclass__ = type
__all__ = [
    'GenericGitCollection',
    ]

from lazr.uri import (
    InvalidURIError,
    URI,
    )
from storm.expr import (
    Count,
    In,
    Join,
    Select,
    )
from zope.component import getUtility
from zope.interface import implements

from lp.app.enums import PRIVATE_INFORMATION_TYPES
from lp.code.interfaces.codehosting import LAUNCHPAD_SERVICES
from lp.code.interfaces.gitcollection import (
    IGitCollection,
    InvalidGitFilter,
    )
from lp.code.interfaces.gitlookup import IGitLookup
from lp.code.interfaces.gitrepository import (
    user_has_special_git_repository_access,
    )
from lp.code.model.gitrepository import (
    GitRepository,
    get_git_repository_privacy_filter,
    )
from lp.registry.enums import EXCLUSIVE_TEAM_POLICY
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.bulk import load_related
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.interfaces import IStore
from lp.services.propertycache import get_property_cache


class GenericGitCollection:
    """See `IGitCollection`."""

    implements(IGitCollection)

    def __init__(self, store=None, filter_expressions=None, tables=None):
        """Construct a `GenericGitCollection`.

        :param store: The store to look in for repositories. If not
            specified, use the default store.
        :param filter_expressions: A list of Storm expressions to
            restrict the repositories in the collection. If unspecified,
            then there will be no restrictions on the result set. That is,
            all repositories in the store will be in the collection.
        :param tables: A dict of Storm tables to the Join expression.  If an
            expression in filter_expressions refers to a table, then that
            table *must* be in this list.
        """
        self._store = store
        if filter_expressions is None:
            filter_expressions = []
        self._filter_expressions = list(filter_expressions)
        if tables is None:
            tables = {}
        self._tables = tables
        self._user = None

    def count(self):
        """See `IGitCollection`."""
        return self.getRepositories(eager_load=False).count()

    def is_empty(self):
        """See `IGitCollection`."""
        return self.getRepositories(eager_load=False).is_empty()

    def ownerCounts(self):
        """See `IGitCollection`."""
        is_team = Person.teamowner != None
        owners = self._getRepositorySelect((GitRepository.owner_id,))
        counts = dict(self.store.find(
            (is_team, Count(Person.id)),
            Person.id.is_in(owners)).group_by(is_team))
        return (counts.get(False, 0), counts.get(True, 0))

    @property
    def store(self):
        # Although you might think we could set the default value for store
        # in the constructor, we can't.  The IStore utility is not available
        # at the time that the ZCML is parsed, which means we get an error
        # if this code is in the constructor.
        # -- JonathanLange 2009-02-17.
        if self._store is None:
            return IStore(GitRepository)
        else:
            return self._store

    def _filterBy(self, expressions, table=None, join=None):
        """Return a subset of this collection, filtered by 'expressions'."""
        # NOTE: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        if table is not None and join is None:
            raise InvalidGitFilter("Cannot specify a table without a join.")
        if expressions is None:
            expressions = []
        tables = self._tables.copy()
        if table is not None:
            tables[table] = join
        return self.__class__(
            self.store, self._filter_expressions + expressions, tables)

    def _getRepositorySelect(self, columns=(GitRepository.id,)):
        """Return a Storm 'Select' for columns in this collection."""
        repositories = self.getRepositories(
            eager_load=False, find_expr=columns)
        return repositories.get_plain_result_set()._get_select()

    def _getRepositoryExpressions(self):
        """Return the where expressions for this collection."""
        return (self._filter_expressions +
            self._getRepositoryVisibilityExpression())

    def _getRepositoryVisibilityExpression(self):
        """Return the where clauses for visibility."""
        return []

    def getRepositories(self, find_expr=GitRepository, eager_load=False):
        """See `IGitCollection`."""
        tables = [GitRepository] + list(set(self._tables.values()))
        expressions = self._getRepositoryExpressions()
        resultset = self.store.using(*tables).find(find_expr, *expressions)

        def do_eager_load(rows):
            repository_ids = set(repository.id for repository in rows)
            if not repository_ids:
                return
            load_related(Product, rows, ['project_id'])
            # So far have only needed the persons for their canonical_url - no
            # need for validity etc in the API call.
            load_related(Person, rows, ['owner_id', 'registrant_id'])

        def cache_permission(repository):
            if self._user:
                get_property_cache(repository)._known_viewers = set(
                    [self._user.id])
            return repository

        eager_load_hook = (
            do_eager_load if eager_load and find_expr == GitRepository
            else None)
        return DecoratedResultSet(
            resultset, pre_iter_hook=eager_load_hook,
            result_decorator=cache_permission)

    def getRepositoryIds(self):
        """See `IGitCollection`."""
        return self.getRepositories(
            find_expr=GitRepository.id).get_plain_result_set()

    def getTeamsWithRepositories(self, person):
        """See `IGitCollection`."""
        # This method doesn't entirely fit with the intent of the
        # GitCollection conceptual model, but we're not quite sure how to
        # fix it just yet.
        repository_query = self._getRepositorySelect((GitRepository.owner_id,))
        return self.store.find(
            Person,
            Person.id == TeamParticipation.teamID,
            TeamParticipation.person == person,
            TeamParticipation.team != person,
            Person.id.is_in(repository_query))

    def inProject(self, project):
        """See `IGitCollection`."""
        return self._filterBy([GitRepository.project == project])

    def inProjectGroup(self, projectgroup):
        """See `IGitCollection`."""
        return self._filterBy(
            [Product.projectgroup == projectgroup.id],
            table=Product,
            join=Join(Product, GitRepository.project == Product.id))

    def inDistribution(self, distribution):
        """See `IGitCollection`."""
        return self._filterBy([GitRepository.distribution == distribution])

    def inDistributionSourcePackage(self, distro_source_package):
        """See `IGitCollection`."""
        distribution = distro_source_package.distribution
        sourcepackagename = distro_source_package.sourcepackagename
        return self._filterBy(
            [GitRepository.distribution == distribution,
             GitRepository.sourcepackagename == sourcepackagename])

    def isPersonal(self):
        """See `IGitCollection`."""
        return self._filterBy(
            [GitRepository.project == None,
             GitRepository.distribution == None])

    def isPrivate(self):
        """See `IGitCollection`."""
        return self._filterBy(
            [GitRepository.information_type.is_in(PRIVATE_INFORMATION_TYPES)])

    def isExclusive(self):
        """See `IGitCollection`."""
        return self._filterBy(
            [Person.membership_policy.is_in(EXCLUSIVE_TEAM_POLICY)],
            table=Person,
            join=Join(Person, GitRepository.owner_id == Person.id))

    def ownedBy(self, person):
        """See `IGitCollection`."""
        return self._filterBy([GitRepository.owner == person])

    def ownedByTeamMember(self, person):
        """See `IGitCollection`."""
        subquery = Select(
            TeamParticipation.teamID,
            where=TeamParticipation.personID == person.id)
        return self._filterBy([In(GitRepository.owner_id, subquery)])

    def registeredBy(self, person):
        """See `IGitCollection`."""
        return self._filterBy([GitRepository.registrant == person])

    def _getExactMatch(self, term):
        # Look up the repository by its URL, which handles both shortcuts
        # and unique names.
        repository = getUtility(IGitLookup).getByUrl(term)
        if repository is not None:
            return repository
        # Fall back to searching by unique_name, stripping out the path if
        # it's a URI.
        try:
            path = URI(term).path.strip("/")
        except InvalidURIError:
            path = term
        return getUtility(IGitLookup).getByUniqueName(path)

    def search(self, term):
        """See `IGitCollection`."""
        repository = self._getExactMatch(term)
        if repository:
            collection = self._filterBy([GitRepository.id == repository.id])
        else:
            term = unicode(term)
            # Filter by name.
            field = GitRepository.name
            # Except if the term contains /, when we use unique_name.
            # XXX cjwatson 2015-02-06: Disabled until the URL format settles
            # down, at which point we can make GitRepository.unique_name a
            # trigger-maintained column rather than a property.
            #if '/' in term:
            #    field = GitRepository.unique_name
            collection = self._filterBy(
                [field.lower().contains_string(term.lower())])
        return collection.getRepositories(eager_load=False).order_by(
            GitRepository.name, GitRepository.id)

    def visibleByUser(self, person):
        """See `IGitCollection`."""
        if (person == LAUNCHPAD_SERVICES or
            user_has_special_git_repository_access(person)):
            return self
        if person is None:
            return AnonymousGitCollection(
                self._store, self._filter_expressions, self._tables)
        return VisibleGitCollection(
            person, self._store, self._filter_expressions, self._tables)

    def withIds(self, *repository_ids):
        """See `IGitCollection`."""
        return self._filterBy([GitRepository.id.is_in(repository_ids)])


class AnonymousGitCollection(GenericGitCollection):
    """Repository collection that only shows public repositories."""

    def _getRepositoryVisibilityExpression(self):
        """Return the where clauses for visibility."""
        return get_git_repository_privacy_filter(None)


class VisibleGitCollection(GenericGitCollection):
    """A repository collection that has special logic for visibility."""

    def __init__(self, user, store=None, filter_expressions=None, tables=None):
        super(VisibleGitCollection, self).__init__(
            store=store, filter_expressions=filter_expressions, tables=tables)
        self._user = user

    def _filterBy(self, expressions, table=None, join=None):
        """Return a subset of this collection, filtered by 'expressions'."""
        # NOTE: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        if table is not None and join is None:
            raise InvalidGitFilter("Cannot specify a table without a join.")
        if expressions is None:
            expressions = []
        tables = self._tables.copy()
        if table is not None:
            tables[table] = join
        return self.__class__(
            self._user, self.store, self._filter_expressions + expressions)

    def _getRepositoryVisibilityExpression(self):
        """Return the where clauses for visibility."""
        return get_git_repository_privacy_filter(self._user)

    def visibleByUser(self, person):
        """See `IGitCollection`."""
        if person == self._user:
            return self
        raise InvalidGitFilter(
            "Cannot filter for Git repositories visible by user %r, already "
            "filtering for %r" % (person, self._user))
