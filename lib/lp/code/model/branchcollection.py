# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    ]

from collections import defaultdict

from storm.expr import (
    And,
    Count,
    Desc,
    In,
    Join,
    LeftJoin,
    Or,
    Select,
    Union,
    )
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.launchpad.searchbuilder import any
from canonical.launchpad.webapp.vocabulary import CountableIterator
from canonical.lazr.utils import safe_hasattr
from lp.bugs.interfaces.bugtask import (
    IBugTaskSet,
    BugTaskSearchParams,
    )
from lp.bugs.model.bugbranch import BugBranch
from lp.bugs.model.bugtask import BugTask
from lp.code.interfaces.branch import user_has_special_branch_access
from lp.code.interfaces.branchcollection import (
    IBranchCollection,
    InvalidFilter,
    )
from lp.code.interfaces.seriessourcepackagebranch import (
    IFindOfficialBranchLinks,
    )
from lp.code.enums import BranchMergeProposalStatus
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.code.interfaces.codehosting import LAUNCHPAD_SERVICES
from lp.code.model.branch import (
    Branch,
    filter_one_task_per_bug,
    )
from lp.code.model.branchmergeproposal import BranchMergeProposal
from lp.code.model.branchsubscription import BranchSubscription
from lp.code.model.codereviewcomment import CodeReviewComment
from lp.code.model.codereviewvote import CodeReviewVoteReference
from lp.code.model.seriessourcepackagebranch import SeriesSourcePackageBranch
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.person import (
    Owner,
    Person,
    )
from lp.registry.model.product import Product
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.registry.model.teammembership import TeamParticipation
from lp.services.propertycache import get_property_cache


class GenericBranchCollection:
    """See `IBranchCollection`."""

    implements(IBranchCollection)

    def __init__(self, store=None, branch_filter_expressions=None,
                 tables=None, exclude_from_search=None):
        """Construct a `GenericBranchCollection`.

        :param store: The store to look in for branches. If not specified,
            use the default store.
        :param branch_filter_expressions: A list of Storm expressions to
            restrict the branches in the collection. If unspecified, then
            there will be no restrictions on the result set. That is, all
            branches in the store will be in the collection.
        :param tables: A dict of Storm tables to the Join expression.  If an
            expression in branch_filter_expressions refers to a table, then
            that table *must* be in this list.
        """
        self._store = store
        if branch_filter_expressions is None:
            branch_filter_expressions = []
        self._branch_filter_expressions = branch_filter_expressions
        if tables is None:
            tables = {}
        self._tables = tables
        if exclude_from_search is None:
            exclude_from_search = []
        self._exclude_from_search = exclude_from_search

    def count(self):
        """See `IBranchCollection`."""
        return self.getBranches(eager_load=False).count()

    def ownerCounts(self):
        """See `IBranchCollection`."""
        is_team = Person.teamowner != None
        branch_owners = self._getBranchIdQuery()
        branch_owners.columns = (Branch.ownerID,)
        counts = dict(self.store.find(
            (is_team, Count(Person.id)),
            Person.id.is_in(branch_owners)).group_by(is_team))
        return (counts.get(False, 0), counts.get(True, 0))

    @property
    def store(self):
        # Although you might think we could set the default value for store in
        # the constructor, we can't. The IStoreSelector utility is not
        # available at the time that the branchcollection.zcml is parsed,
        # which means we get an error if this code is in the constructor.
        # -- JonathanLange 2009-02-17.
        if self._store is None:
            return getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        else:
            return self._store

    def _filterBy(self, expressions, table=None, join=None,
                  exclude_from_search=None):
        """Return a subset of this collection, filtered by 'expressions'."""
        # NOTE: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        tables = self._tables.copy()
        if table is not None:
            if join is None:
                raise InvalidFilter("Cannot specify a table without a join.")
            tables[table] = join
        if exclude_from_search is None:
            exclude_from_search = []
        if expressions is None:
            expressions = []
        return self.__class__(
            self.store,
            self._branch_filter_expressions + expressions,
            tables,
            self._exclude_from_search + exclude_from_search)

    def _getBranchIdQuery(self):
        """Return a Storm 'Select' for the branch IDs in this collection."""
        select = self.getBranches(eager_load=False)._get_select()
        select.columns = (Branch.id,)
        return select

    def _getBranchExpressions(self):
        """Return the where expressions for this collection."""
        return self._branch_filter_expressions

    def getBranches(self, eager_load=False):
        """See `IBranchCollection`."""
        tables = [Branch] + self._tables.values()
        expressions = self._getBranchExpressions()
        resultset = self.store.using(*tables).find(Branch, *expressions)
        if not eager_load:
            return resultset

        def do_eager_load(rows):
            branch_ids = set(branch.id for branch in rows)
            if not branch_ids:
                return
            branches = dict((branch.id, branch) for branch in rows)
            caches = dict((branch.id, get_property_cache(branch))
                for branch in rows)
            for cache in caches.values():
                if not safe_hasattr(cache, '_associatedProductSeries'):
                    cache._associatedProductSeries = []
                if not safe_hasattr(cache, '_associatedSuiteSourcePackages'):
                    cache._associatedSuiteSourcePackages = []
            # associatedProductSeries
            # Imported here to avoid circular import.
            from lp.registry.model.productseries import ProductSeries
            for productseries in self.store.find(
                ProductSeries,
                ProductSeries.branchID.is_in(branch_ids)):
                cache = caches[productseries.branchID]
                cache._associatedProductSeries.append(productseries)
            # associatedSuiteSourcePackages
            series_set = getUtility(IFindOfficialBranchLinks)
            # Order by the pocket to get the release one first. If changing
            # this be sure to also change BranchCollection.getBranches.
            links = series_set.findForBranches(rows).order_by(
                SeriesSourcePackageBranch.pocket)
            for link in links:
                cache = caches[link.branchID]
                cache._associatedSuiteSourcePackages.append(
                    link.suite_sourcepackage)
        return DecoratedResultSet(resultset, pre_iter_hook=do_eager_load)

    def getMergeProposals(self, statuses=None, for_branches=None,
                          target_branch=None, merged_revnos=None):
        """See `IBranchCollection`."""
        expressions = [
            BranchMergeProposal.source_branchID.is_in(
                self._getBranchIdQuery()),
            ]
        if for_branches is not None:
            branch_ids = [branch.id for branch in for_branches]
            expressions.append(
                BranchMergeProposal.source_branchID.is_in(branch_ids))
        if target_branch is not None:
            expressions.append(
                BranchMergeProposal.target_branch == target_branch)
        if merged_revnos is not None:
            expressions.append(
                BranchMergeProposal.merged_revno.is_in(merged_revnos))
        expressions.extend(self._getExtraMergeProposalExpressions())
        if statuses is not None:
            expressions.append(
                BranchMergeProposal.queue_status.is_in(statuses))
        return self.store.find(BranchMergeProposal, expressions)

    def _getExtraMergeProposalExpressions(self):
        """Extra storm expressions needed for merge proposal queries.

        Used primarily by the visibility check for target branches.
        """
        return []

    def getMergeProposalsForPerson(self, person, status=None):
        """See `IBranchCollection`."""
        # We want to limit the proposals to those where the source branch is
        # limited by the defined collection.
        owned = self.ownedBy(person).getMergeProposals(status)
        reviewing = self.getMergeProposalsForReviewer(person, status)
        return owned.union(reviewing)

    def getMergeProposalsForReviewer(self, reviewer, status=None):
        """See `IBranchCollection`."""
        tables = [
            BranchMergeProposal,
            Join(CodeReviewVoteReference,
                 CodeReviewVoteReference.branch_merge_proposalID == \
                 BranchMergeProposal.id),
            LeftJoin(CodeReviewComment,
                 CodeReviewVoteReference.commentID == CodeReviewComment.id)]

        expressions = [
            CodeReviewVoteReference.reviewer == reviewer,
            BranchMergeProposal.source_branchID.is_in(
                self._getBranchIdQuery())]
        expressions.extend(self._getExtraMergeProposalExpressions())
        if status is not None:
            expressions.append(
                BranchMergeProposal.queue_status.is_in(status))
        proposals = self.store.using(*tables).find(
            BranchMergeProposal, expressions)
        # Apply sorting here as we can't do it in the browser code.  We need
        # to think carefully about the best places to do this, but not here
        # nor now.
        proposals.order_by(Desc(CodeReviewComment.vote))
        return proposals

    def getExtendedRevisionDetails(self, user, revisions):
        """See `IBranchCollection`."""

        if not revisions:
            return []
        branch = revisions[0].branch

        def make_rev_info(
                branch_revision, merge_proposal_revs, linked_bugtasks):
            rev_info = {
                'revision': branch_revision,
                'linked_bugtasks': None,
                'merge_proposal': None,
                }
            merge_proposal = merge_proposal_revs.get(branch_revision.sequence)
            rev_info['merge_proposal'] = merge_proposal
            if merge_proposal is not None:
                rev_info['linked_bugtasks'] = linked_bugtasks.get(
                    merge_proposal.source_branch.id)
            return rev_info

        rev_nos = [revision.sequence for revision in revisions]
        merge_proposals = self.getMergeProposals(
                target_branch=branch, merged_revnos=rev_nos,
                statuses=[BranchMergeProposalStatus.MERGED])
        merge_proposal_revs = dict(
                [(mp.merged_revno, mp) for mp in merge_proposals])
        source_branch_ids = [mp.source_branch.id for mp in merge_proposals]
        linked_bugtasks = defaultdict(list)

        if source_branch_ids:
            # We get the bugtasks for our merge proposal branches

            # First, the bug ids
            params = BugTaskSearchParams(
                user=user, status=None,
                linked_branches=any(*source_branch_ids))
            bug_ids = getUtility(IBugTaskSet).searchBugIds(params)

            # Then the bug tasks and branches
            store = IStore(BugBranch)
            rs = store.using(
                BugBranch,
                Join(BugTask, BugTask.bugID == BugBranch.bugID),
            ).find(
                (BugTask, BugBranch),
                BugBranch.bugID.is_in(bug_ids),
                BugBranch.branchID.is_in(source_branch_ids)
            )

            # Build up a collection of bugtasks for each branch
            bugtasks_for_branch = defaultdict(list)
            for bugtask, bugbranch in rs:
                bugtasks_for_branch[bugbranch.branch].append(bugtask)

            # Now filter those down to one bugtask per branch
            for branch, tasks in bugtasks_for_branch.iteritems():
                linked_bugtasks[branch.id].extend(
                    filter_one_task_per_bug(branch, tasks))

        return [make_rev_info(
                rev, merge_proposal_revs, linked_bugtasks)
                for rev in revisions]

    def getTeamsWithBranches(self, person):
        """See `IBranchCollection`."""
        # This method doesn't entirely fit with the intent of the
        # BranchCollection conceptual model, but we're not quite sure how to
        # fix it just yet.  Perhaps when bug 337494 is fixed, we'd be able to
        # sensibly be able to move this method to another utility class.
        branch_query = self._getBranchIdQuery()
        branch_query.columns = (Branch.ownerID,)
        return self.store.find(
            Person,
            Person.id == TeamParticipation.teamID,
            TeamParticipation.person == person,
            TeamParticipation.team != person,
            Person.id.is_in(branch_query))

    def inProduct(self, product):
        """See `IBranchCollection`."""
        return self._filterBy(
            [Branch.product == product], exclude_from_search=['product'])

    def inProject(self, project):
        """See `IBranchCollection`."""
        return self._filterBy(
            [Product.project == project.id],
            table=Product,
            join=Join(Product, Branch.product == Product.id))

    def inDistribution(self, distribution):
        """See `IBranchCollection`."""
        return self._filterBy(
            [DistroSeries.distribution == distribution],
            table=Distribution,
            join=Join(DistroSeries, Branch.distroseries == DistroSeries.id))

    def inDistroSeries(self, distro_series):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.distroseries == distro_series])

    def inDistributionSourcePackage(self, distro_source_package):
        """See `IBranchCollection`."""
        distribution = distro_source_package.distribution
        sourcepackagename = distro_source_package.sourcepackagename
        return self._filterBy(
            [DistroSeries.distribution == distribution,
             Branch.sourcepackagename == sourcepackagename],
            table=Distribution,
            join=Join(DistroSeries, Branch.distroseries == DistroSeries.id))

    def officialBranches(self, pocket=None):
        """See `IBranchCollection`"""
        if pocket is None:
            expressions = []
        else:
            expressions = [SeriesSourcePackageBranch.pocket == pocket]
        return self._filterBy(
            expressions,
            table=SeriesSourcePackageBranch,
            join=Join(SeriesSourcePackageBranch,
                      SeriesSourcePackageBranch.branch == Branch.id))

    def inSourcePackage(self, source_package):
        """See `IBranchCollection`."""
        return self._filterBy([
            Branch.distroseries == source_package.distroseries,
            Branch.sourcepackagename == source_package.sourcepackagename])

    def isJunk(self):
        """See `IBranchCollection`."""
        return self._filterBy([
            Branch.product == None,
            Branch.sourcepackagename == None])

    def ownedBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.owner == person])

    def ownedByTeamMember(self, person):
        """See `IBranchCollection`."""
        subquery = Select(
            TeamParticipation.teamID,
            where=TeamParticipation.personID==person.id)
        filter = [In(Branch.ownerID, subquery)]

        return self._filterBy(filter)

    def registeredBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.registrant == person])

    def relatedTo(self, person):
        """See `IBranchCollection`."""
        return self._filterBy(
            [Branch.id.is_in(
                Union(
                    Select(Branch.id, Branch.owner == person),
                    Select(Branch.id, Branch.registrant == person),
                    Select(Branch.id,
                           And(BranchSubscription.person == person,
                               BranchSubscription.branch == Branch.id))))])

    def _getExactMatch(self, search_term):
        """Return the exact branch that 'search_term' matches, or None."""
        search_term = search_term.rstrip('/')
        branch_set = getUtility(IBranchLookup)
        branch = branch_set.getByUniqueName(search_term)
        if branch is None:
            branch = branch_set.getByUrl(search_term)
        return branch

    def search(self, search_term):
        """See `IBranchCollection`."""
        # XXX: JonathanLange 2009-02-23 bug 372591: This matches the old
        # search algorithm that used to live in vocabularies/dbojects.py. It's
        # not actually very good -- really it should match based on substrings
        # of the unique name and sort based on relevance.
        branch = self._getExactMatch(search_term)
        if branch is not None:
            if branch in self.getBranches(eager_load=False):
                return CountableIterator(1, [branch])
            else:
                return CountableIterator(0, [])
        like_term = '%' + search_term + '%'
        # Match the Branch name or the URL.
        queries = [Select(Branch.id,
                          Or(Branch.name.like(like_term),
                             Branch.url == search_term))]
        # Match the product name.
        if 'product' not in self._exclude_from_search:
            queries.append(Select(
                Branch.id,
                And(Branch.product == Product.id,
                    Product.name.like(like_term))))

        # Match the owner name.
        queries.append(Select(
            Branch.id,
            And(Branch.owner == Owner.id, Owner.name.like(like_term))))

        # Match the package bits.
        queries.append(
            Select(Branch.id,
                   And(Branch.sourcepackagename == SourcePackageName.id,
                       Branch.distroseries == DistroSeries.id,
                       DistroSeries.distribution == Distribution.id,
                       Or(SourcePackageName.name.like(like_term),
                          DistroSeries.name.like(like_term),
                          Distribution.name.like(like_term)))))

        # Get the results.
        collection = self._filterBy([Branch.id.is_in(Union(*queries))])
        results = collection.getBranches(eager_load=False).order_by(
            Branch.name, Branch.id)
        return CountableIterator(results.count(), results)

    def scanned(self):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.last_scanned != None])

    def subscribedBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy(
            [BranchSubscription.person == person],
            table=BranchSubscription,
            join=Join(BranchSubscription,
                      BranchSubscription.branch == Branch.id))

    def targetedBy(self, person, since=None):
        """See `IBranchCollection`."""
        clauses = [BranchMergeProposal.registrant == person]
        if since is not None:
            clauses.append(BranchMergeProposal.date_created >= since)
        return self._filterBy(
            clauses,
            table=BranchMergeProposal,
            join=Join(BranchMergeProposal,
                      BranchMergeProposal.target_branch == Branch.id))

    def visibleByUser(self, person):
        """See `IBranchCollection`."""
        if (person == LAUNCHPAD_SERVICES or
            user_has_special_branch_access(person)):
            return self
        if person is None:
            return AnonymousBranchCollection(
                self._store, self._branch_filter_expressions,
                self._tables, self._exclude_from_search)
        return VisibleBranchCollection(
            person, self._store, self._branch_filter_expressions,
            self._tables, self._exclude_from_search)

    def withBranchType(self, *branch_types):
        return self._filterBy([Branch.branch_type.is_in(branch_types)])

    def withLifecycleStatus(self, *statuses):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.lifecycle_status.is_in(statuses)])

    def modifiedSince(self, epoch):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.date_last_modified > epoch])

    def scannedSince(self, epoch):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.last_scanned > epoch])


class AnonymousBranchCollection(GenericBranchCollection):
    """Branch collection that only shows public branches."""

    def __init__(self, store=None, branch_filter_expressions=None,
                 tables=None, exclude_from_search=None):
        super(AnonymousBranchCollection, self).__init__(
            store=store,
            branch_filter_expressions=list(branch_filter_expressions),
            tables=tables, exclude_from_search=exclude_from_search)
        self._branch_filter_expressions.append(Branch.private == False)

    def _getExtraMergeProposalExpressions(self):
        """Extra storm expressions needed for merge proposal queries.

        Used primarily by the visibility check for target branches.
        """
        return [
            BranchMergeProposal.target_branchID.is_in(
                Select(Branch.id, Branch.private == False))]


class VisibleBranchCollection(GenericBranchCollection):
    """A branch collection that has special logic for visibility."""

    def __init__(self, user, store=None, branch_filter_expressions=None,
                 tables=None, exclude_from_search=None):
        super(VisibleBranchCollection, self).__init__(
            store=store, branch_filter_expressions=branch_filter_expressions,
            tables=tables, exclude_from_search=exclude_from_search)
        self._user = user
        self._private_branch_ids = self._getPrivateBranchSubQuery()

    def _filterBy(self, expressions, table=None, join=None,
                  exclude_from_search=None):
        """Return a subset of this collection, filtered by 'expressions'."""
        # NOTE: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        tables = self._tables.copy()
        if table is not None:
            if join is None:
                raise InvalidFilter("Cannot specify a table without a join.")
            tables[table] = join
        if exclude_from_search is None:
            exclude_from_search = []
        if expressions is None:
            expressions = []
        return self.__class__(
            self._user,
            self.store,
            self._branch_filter_expressions + expressions,
            tables,
            self._exclude_from_search + exclude_from_search)

    def _getPrivateBranchSubQuery(self):
        """Return a subquery to get the private branches the user can see.

        If the user is None (which is used for anonymous access), then there
        is no subquery.  Otherwise return the branch ids for the private
        branches that the user owns or is subscribed to.
        """
        # Everyone can see public branches.
        person = self._user
        if person is None:
            # Anonymous users can only see the public branches.
            return None

        # A union is used here rather than the more simplistic simple joins
        # due to the query plans generated.  If we just have a simple query
        # then we are joining across TeamParticipation and BranchSubscription.
        # This creates a bad plan, hence the use of a union.
        private_branches = Union(
            # Private branches the person owns (or a team the person is in).
            Select(Branch.id,
                   And(Branch.owner == TeamParticipation.teamID,
                       TeamParticipation.person == person,
                       Branch.private == True)),
            # Private branches the person is subscribed to, either directly or
            # indirectly.
            Select(Branch.id,
                   And(BranchSubscription.branch == Branch.id,
                       BranchSubscription.person ==
                       TeamParticipation.teamID,
                       TeamParticipation.person == person,
                       Branch.private == True)))
        return private_branches

    def _getBranchExpressions(self):
        """Return the where expressions for this collection."""
        public_branches = Branch.private == False
        if self._private_branch_ids is None:
            # Public only.
            return self._branch_filter_expressions + [public_branches]
        else:
            public_or_private = Or(
                public_branches,
                Branch.id.is_in(self._private_branch_ids))
            return self._branch_filter_expressions + [public_or_private]

    def visibleByUser(self, person):
        """See `IBranchCollection`."""
        if person == self._user:
            return self
        raise InvalidFilter(
            "Cannot filter for branches visible by user %r, already "
            "filtering for %r" % (person, self._user))

    def _getExtraMergeProposalExpressions(self):
        """Extra storm expressions needed for merge proposal queries.

        Used primarily by the visibility check for target branches.
        """
        if self._private_branch_ids is None:
            # Public only.
            visible_branches = Select(Branch.id, Branch.private == False)
        else:
            visible_branches = Select(
                Branch.id,
                Or(Branch.private == False,
                   Branch.id.is_in(self._private_branch_ids)))
        return [
            BranchMergeProposal.target_branchID.is_in(visible_branches)]
