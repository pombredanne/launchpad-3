# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementations of `IGitCollection`."""

__metaclass__ = type
__all__ = [
    'GenericGitCollection',
    ]

from functools import partial
from operator import attrgetter

from lazr.uri import (
    InvalidURIError,
    URI,
    )
from storm.expr import (
    And,
    Count,
    Desc,
    In,
    Join,
    LeftJoin,
    Select,
    SQL,
    With,
    )
from storm.info import ClassAlias
from storm.store import EmptyResultSet
from zope.component import getUtility
from zope.interface import implementer

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
from lp.code.model.branchmergeproposal import BranchMergeProposal
from lp.code.model.codeimport import CodeImport
from lp.code.model.codereviewcomment import CodeReviewComment
from lp.code.model.codereviewvote import CodeReviewVoteReference
from lp.code.model.gitrepository import (
    get_git_repository_privacy_filter,
    GitRepository,
    )
from lp.code.model.gitsubscription import GitSubscription
from lp.registry.enums import EXCLUSIVE_TEAM_POLICY
from lp.registry.model.distribution import Distribution
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.bulk import load_related
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.interfaces import IStore
from lp.services.propertycache import get_property_cache


@implementer(IGitCollection)
class GenericGitCollection:
    """See `IGitCollection`."""

    def __init__(self, store=None, filter_expressions=None, tables=None,
                 asymmetric_filter_expressions=None, asymmetric_tables=None):
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
        :param asymmetric_filter_expressions: As per filter_expressions but
            only applies to one side of reflexive joins.
        :param asymmetric_tables: As per tables, for
            asymmetric_filter_expressions.
        """
        self._store = store
        if filter_expressions is None:
            filter_expressions = []
        self._filter_expressions = list(filter_expressions)
        if tables is None:
            tables = {}
        self._tables = tables
        if asymmetric_filter_expressions is None:
            asymmetric_filter_expressions = []
        self._asymmetric_filter_expressions = list(
            asymmetric_filter_expressions)
        if asymmetric_tables is None:
            asymmetric_tables = {}
        self._asymmetric_tables = asymmetric_tables
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

    def _filterBy(self, expressions, table=None, join=None, symmetric=True):
        """Return a subset of this collection, filtered by 'expressions'.

        :param symmetric: If True, this filter will apply to both sides of
            merge proposal lookups and any other lookups that join
            GitRepository back onto GitRepository.
        """
        # NOTE: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        if table is not None and join is None:
            raise InvalidGitFilter("Cannot specify a table without a join.")
        if expressions is None:
            expressions = []
        tables = self._tables.copy()
        asymmetric_tables = self._asymmetric_tables.copy()
        if symmetric:
            if table is not None:
                tables[table] = join
            symmetric_expr = self._filter_expressions + expressions
            asymmetric_expr = list(self._asymmetric_filter_expressions)
        else:
            if table is not None:
                asymmetric_tables[table] = join
            symmetric_expr = list(self._filter_expressions)
            asymmetric_expr = (
                self._asymmetric_filter_expressions + expressions)
        if table is not None:
            tables[table] = join
        return self.__class__(
            self.store, symmetric_expr, tables,
            asymmetric_expr, asymmetric_tables)

    def _getRepositorySelect(self, columns=(GitRepository.id,)):
        """Return a Storm 'Select' for columns in this collection."""
        repositories = self.getRepositories(
            eager_load=False, find_expr=columns)
        return repositories.get_plain_result_set()._get_select()

    def _getRepositoryExpressions(self):
        """Return the where expressions for this collection."""
        return (self._filter_expressions +
            self._asymmetric_filter_expressions +
            self._getRepositoryVisibilityExpression())

    def _getRepositoryVisibilityExpression(self, repository_class=None):
        """Return the where clauses for visibility."""
        return []

    @staticmethod
    def preloadVisibleRepositories(repositories, user=None):
        """Preload visibility for the given list of repositories."""
        if len(repositories) == 0:
            return
        expressions = [
            GitRepository.id.is_in(map(attrgetter("id"), repositories))]
        if user is None:
            collection = AnonymousGitCollection(filter_expressions=expressions)
        else:
            collection = VisibleGitCollection(
                user=user, filter_expressions=expressions)
        return list(collection.getRepositories())

    @staticmethod
    def preloadDataForRepositories(repositories):
        """Preload repositories' cached associated targets."""
        load_related(Distribution, repositories, ['distribution_id'])
        load_related(SourcePackageName, repositories, ['sourcepackagename_id'])
        load_related(Product, repositories, ['project_id'])
        caches = {
            repository.id: get_property_cache(repository)
            for repository in repositories}
        repository_ids = caches.keys()
        for cache in caches.values():
            cache.code_import = None
        for code_import in IStore(CodeImport).find(
                CodeImport, CodeImport.git_repositoryID.is_in(repository_ids)):
            caches[code_import.git_repositoryID].code_import = code_import

    def getRepositories(self, find_expr=GitRepository, eager_load=False,
                        order_by_date=False, order_by_id=False):
        """See `IGitCollection`."""
        all_tables = set(
            self._tables.values() + self._asymmetric_tables.values())
        tables = [GitRepository] + list(all_tables)
        expressions = self._getRepositoryExpressions()
        resultset = self.store.using(*tables).find(find_expr, *expressions)
        assert not order_by_date or not order_by_id
        if order_by_date:
            resultset.order_by(Desc(GitRepository.date_last_modified))
        elif order_by_id:
            resultset.order_by(GitRepository.id)

        def do_eager_load(rows):
            repository_ids = set(repository.id for repository in rows)
            if not repository_ids:
                return
            GenericGitCollection.preloadDataForRepositories(rows)
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

    def getMergeProposals(self, statuses=None, target_repository=None,
                          target_path=None, prerequisite_repository=None,
                          prerequisite_path=None, merged_revision_ids=None,
                          merge_proposal_ids=None, eager_load=False):
        """See `IGitCollection`."""
        if merged_revision_ids is not None and not merged_revision_ids:
            # We have an empty revision list, so we can shortcut.
            return EmptyResultSet()
        elif (self._asymmetric_filter_expressions or
            target_repository is not None or
            target_path is not None or
            prerequisite_repository is not None or
            prerequisite_path is not None or
            merged_revision_ids is not None or
            merge_proposal_ids is not None):
            return self._naiveGetMergeProposals(
                statuses, target_repository, target_path,
                prerequisite_repository, prerequisite_path,
                merged_revision_ids, merge_proposal_ids, eager_load=eager_load)
        else:
            # When examining merge proposals in a scope, this is a moderately
            # effective set of constrained queries.  It is not effective when
            # unscoped or when tight constraints on repositories are present.
            return self._scopedGetMergeProposals(
                statuses, eager_load=eager_load)

    def _naiveGetMergeProposals(self, statuses=None, target_repository=None,
                                target_path=None, prerequisite_repository=None,
                                prerequisite_path=None,
                                merged_revision_ids=None,
                                merge_proposal_ids=None, eager_load=False):
        Target = ClassAlias(GitRepository, "target")
        extra_tables = list(set(
            self._tables.values() + self._asymmetric_tables.values()))
        tables = [GitRepository] + extra_tables + [
            Join(BranchMergeProposal, And(
                GitRepository.id ==
                    BranchMergeProposal.source_git_repositoryID,
                *(self._filter_expressions +
                  self._asymmetric_filter_expressions))),
            Join(Target,
                Target.id == BranchMergeProposal.target_git_repositoryID),
            ]
        expressions = self._getRepositoryVisibilityExpression()
        expressions.extend(self._getRepositoryVisibilityExpression(Target))
        if target_repository is not None:
            expressions.append(
                BranchMergeProposal.target_git_repository == target_repository)
        if target_path is not None:
            expressions.append(
                BranchMergeProposal.target_git_path == target_path)
        if prerequisite_repository is not None:
            expressions.append(
                BranchMergeProposal.prerequisite_git_repository ==
                    prerequisite_repository)
        if prerequisite_path is not None:
            expressions.append(
                BranchMergeProposal.prerequisite_git_path == prerequisite_path)
        if merged_revision_ids is not None:
            expressions.append(
                BranchMergeProposal.merged_revision_id.is_in(
                    merged_revision_ids))
        if merge_proposal_ids is not None:
            expressions.append(
                BranchMergeProposal.id.is_in(merge_proposal_ids))
        if statuses is not None:
            expressions.append(
                BranchMergeProposal.queue_status.is_in(statuses))
        resultset = self.store.using(*tables).find(
            BranchMergeProposal, *expressions)
        if not eager_load:
            return resultset
        else:
            loader = partial(
                BranchMergeProposal.preloadDataForBMPs, user=self._user)
            return DecoratedResultSet(resultset, pre_iter_hook=loader)

    def _scopedGetMergeProposals(self, statuses, eager_load=False):
        expressions = (
            self._filter_expressions
            + self._getRepositoryVisibilityExpression())
        with_expr = With(
            "candidate_repositories",
            Select(
                GitRepository.id,
                tables=[GitRepository] + self._tables.values(),
                where=And(*expressions) if expressions else True))
        expressions = [SQL("""
            source_git_repository IN
                (SELECT id FROM candidate_repositories) AND
            target_git_repository IN
                (SELECT id FROM candidate_repositories)""")]
        tables = [BranchMergeProposal]
        if self._asymmetric_filter_expressions:
            # Need to filter on GitRepository beyond the with constraints.
            expressions += self._asymmetric_filter_expressions
            expressions.append(
                BranchMergeProposal.source_git_repositoryID ==
                    GitRepository.id)
            tables.append(GitRepository)
            tables.extend(self._asymmetric_tables.values())
        if statuses is not None:
            expressions.append(
                BranchMergeProposal.queue_status.is_in(statuses))
        resultset = self.store.with_(with_expr).using(*tables).find(
            BranchMergeProposal, *expressions)
        if not eager_load:
            return resultset
        else:
            loader = partial(
                BranchMergeProposal.preloadDataForBMPs, user=self._user)
            return DecoratedResultSet(resultset, pre_iter_hook=loader)

    def getMergeProposalsForPerson(self, person, status=None,
                                   eager_load=False):
        """See `IGitCollection`."""
        # We want to limit the proposals to those where the source repository
        # is limited by the defined collection.
        owned = self.ownedBy(person).getMergeProposals(status)
        reviewing = self.getMergeProposalsForReviewer(person, status)
        resultset = owned.union(reviewing)

        if not eager_load:
            return resultset
        else:
            loader = partial(
                BranchMergeProposal.preloadDataForBMPs, user=self._user)
            return DecoratedResultSet(resultset, pre_iter_hook=loader)

    def getMergeProposalsForReviewer(self, reviewer, status=None):
        """See `IGitCollection`."""
        tables = [
            BranchMergeProposal,
            Join(CodeReviewVoteReference,
                 CodeReviewVoteReference.branch_merge_proposalID == \
                 BranchMergeProposal.id),
            LeftJoin(CodeReviewComment,
                 CodeReviewVoteReference.commentID == CodeReviewComment.id)]

        expressions = [
            CodeReviewVoteReference.reviewer == reviewer,
            BranchMergeProposal.source_git_repositoryID.is_in(
                self._getRepositorySelect())]
        visibility = self._getRepositoryVisibilityExpression()
        if visibility:
            expressions.append(
                BranchMergeProposal.target_git_repositoryID.is_in(
                    Select(GitRepository.id, visibility)))
        if status is not None:
            expressions.append(
                BranchMergeProposal.queue_status.is_in(status))
        proposals = self.store.using(*tables).find(
            BranchMergeProposal, *expressions)
        # Apply sorting here as we can't do it in the browser code.  We need to
        # think carefully about the best places to do this, but not here nor
        # now.
        proposals.order_by(Desc(CodeReviewComment.vote))
        return proposals

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
        return self._filterBy([GitRepository.owner == person], symmetric=False)

    def ownedByTeamMember(self, person):
        """See `IGitCollection`."""
        subquery = Select(
            TeamParticipation.teamID,
            where=TeamParticipation.personID == person.id)
        return self._filterBy(
            [In(GitRepository.owner_id, subquery)], symmetric=False)

    def registeredBy(self, person):
        """See `IGitCollection`."""
        return self._filterBy(
            [GitRepository.registrant == person], symmetric=False)

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

    def subscribedBy(self, person):
        """See `IGitCollection`."""
        return self._filterBy(
            [GitSubscription.person == person],
            table=GitSubscription,
            join=Join(GitSubscription,
                      GitSubscription.repository == GitRepository.id),
            symmetric=False)

    def targetedBy(self, person, since=None):
        """See `IGitCollection`."""
        clauses = [BranchMergeProposal.registrant == person]
        if since is not None:
            clauses.append(BranchMergeProposal.date_created >= since)
        return self._filterBy(
            clauses,
            table=BranchMergeProposal,
            join=Join(
                BranchMergeProposal,
                BranchMergeProposal.target_git_repository == GitRepository.id),
            symmetric=False)

    def visibleByUser(self, person):
        """See `IGitCollection`."""
        if (person == LAUNCHPAD_SERVICES or
            user_has_special_git_repository_access(person)):
            return self
        if person is None:
            return AnonymousGitCollection(
                self._store, self._filter_expressions, self._tables,
                self._asymmetric_filter_expressions, self._asymmetric_tables)
        return VisibleGitCollection(
            person, self._store, self._filter_expressions, self._tables,
            self._asymmetric_filter_expressions, self._asymmetric_tables)

    def withIds(self, *repository_ids):
        """See `IGitCollection`."""
        return self._filterBy(
            [GitRepository.id.is_in(repository_ids)], symmetric=False)


class AnonymousGitCollection(GenericGitCollection):
    """Repository collection that only shows public repositories."""

    def _getRepositoryVisibilityExpression(self,
                                           repository_class=GitRepository):
        """Return the where clauses for visibility."""
        return get_git_repository_privacy_filter(
            None, repository_class=repository_class)


class VisibleGitCollection(GenericGitCollection):
    """A repository collection that has special logic for visibility."""

    def __init__(self, user, store=None, filter_expressions=None, tables=None,
                 asymmetric_filter_expressions=None, asymmetric_tables=None):
        super(VisibleGitCollection, self).__init__(
            store=store, filter_expressions=filter_expressions, tables=tables,
            asymmetric_filter_expressions=asymmetric_filter_expressions,
            asymmetric_tables=asymmetric_tables)
        self._user = user

    def _filterBy(self, expressions, table=None, join=None, symmetric=True):
        """Return a subset of this collection, filtered by 'expressions'.

        :param symmetric: If True this filter will apply to both sides of
            merge proposal lookups and any other lookups that join
            GitRepository back onto GitRepository.
        """
        # NOTE: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        if table is not None and join is None:
            raise InvalidGitFilter("Cannot specify a table without a join.")
        if expressions is None:
            expressions = []
        tables = self._tables.copy()
        asymmetric_tables = self._asymmetric_tables.copy()
        if symmetric:
            if table is not None:
                tables[table] = join
            symmetric_expr = self._filter_expressions + expressions
            asymmetric_expr = list(self._asymmetric_filter_expressions)
        else:
            if table is not None:
                asymmetric_tables[table] = join
            symmetric_expr = list(self._filter_expressions)
            asymmetric_expr = self._asymmetric_filter_expressions + expressions
        return self.__class__(
            self._user, self.store, symmetric_expr, tables,
            asymmetric_expr, asymmetric_tables)

    def _getRepositoryVisibilityExpression(self,
                                           repository_class=GitRepository):
        """Return the where clauses for visibility.

        :param repository_class: The GitRepository class to use - permits
            using ClassAliases.
        """
        return get_git_repository_privacy_filter(
            self._user, repository_class=repository_class)

    def visibleByUser(self, person):
        """See `IGitCollection`."""
        if person == self._user:
            return self
        raise InvalidGitFilter(
            "Cannot filter for Git repositories visible by user %r, already "
            "filtering for %r" % (person, self._user))
