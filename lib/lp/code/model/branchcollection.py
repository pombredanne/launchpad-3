# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    ]

from collections import defaultdict

from lazr.restful.utils import safe_hasattr
from storm.expr import (
    And,
    Count,
    Desc,
    In,
    Join,
    LeftJoin,
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

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.searchbuilder import any
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.launchpad.webapp.vocabulary import CountableIterator
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams,
    IBugTaskSet,
    )
from lp.bugs.interfaces.bugtaskfilter import filter_bugtasks_by_context
from lp.bugs.model.bugbranch import BugBranch
from lp.bugs.model.bugtask import BugTask
from lp.code.enums import BranchMergeProposalStatus
from lp.code.interfaces.branch import user_has_special_branch_access
from lp.code.interfaces.branchcollection import (
    IBranchCollection,
    InvalidFilter,
    )
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.code.interfaces.codehosting import LAUNCHPAD_SERVICES
from lp.code.interfaces.seriessourcepackagebranch import (
    IFindOfficialBranchLinks,
    )
from lp.code.model.branch import Branch
from lp.code.model.branchmergeproposal import BranchMergeProposal
from lp.code.model.branchsubscription import BranchSubscription
from lp.code.model.codeimport import CodeImport
from lp.code.model.codereviewcomment import CodeReviewComment
from lp.code.model.codereviewvote import CodeReviewVoteReference
from lp.code.model.diff import (
    Diff,
    PreviewDiff,
    )
from lp.code.model.seriessourcepackagebranch import SeriesSourcePackageBranch
from lp.registry.interfaces.person import IPersonSet
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.person import (
    Owner,
    Person,
    ValidPersonCache,
    )
from lp.registry.model.product import Product
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.bulk import (
    load_referencing,
    load_related,
    )
from lp.services.propertycache import get_property_cache


class GenericBranchCollection:
    """See `IBranchCollection`."""

    implements(IBranchCollection)

    def __init__(self, store=None, branch_filter_expressions=None,
                 tables=None, exclude_from_search=None,
                 asymmetric_filter_expressions=None, asymmetric_tables=None):
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
        :param asymmetric_filter_expressions: As per branch_filter_expressions
            but only applies to one side of reflexive joins.
        :param asymmetric_tables: As per tables, for
            asymmetric_filter_expressions.
        """
        self._store = store
        if branch_filter_expressions is None:
            branch_filter_expressions = []
        self._branch_filter_expressions = list(branch_filter_expressions)
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
        if exclude_from_search is None:
            exclude_from_search = []
        self._exclude_from_search = exclude_from_search

    def count(self):
        """See `IBranchCollection`."""
        return self.getBranches(eager_load=False).count()

    def is_empty(self):
        """See `IBranchCollection`."""
        return self.getBranches(eager_load=False).is_empty()

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
                  exclude_from_search=None, symmetric=True):
        """Return a subset of this collection, filtered by 'expressions'.

        :param symmetric: If True this filter will apply to both sides
            of merge proposal lookups and any other lookups that join
            Branch back onto Branch.
        """
        # NOTE: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        if table is not None:
            if join is None:
                raise InvalidFilter("Cannot specify a table without a join.")
        if expressions is None:
            expressions = []
        tables = self._tables.copy()
        asymmetric_tables = self._asymmetric_tables.copy()
        if symmetric:
            if table is not None:
                tables[table] = join
            symmetric_expr = self._branch_filter_expressions + expressions
            asymmetric_expr = list(self._asymmetric_filter_expressions)
        else:
            if table is not None:
                asymmetric_tables[table] = join
            symmetric_expr = list(self._branch_filter_expressions)
            asymmetric_expr = (
                self._asymmetric_filter_expressions + expressions)
        if exclude_from_search is None:
            exclude_from_search = []
        return self.__class__(
            self.store,
            symmetric_expr,
            tables,
            self._exclude_from_search + exclude_from_search,
            asymmetric_expr,
            asymmetric_tables)

    def _getBranchIdQuery(self):
        """Return a Storm 'Select' for the branch IDs in this collection."""
        select = self.getBranches(eager_load=False)._get_select()
        select.columns = (Branch.id,)
        return select

    def _getBranchExpressions(self):
        """Return the where expressions for this collection."""
        return (self._branch_filter_expressions +
            self._asymmetric_filter_expressions +
            self._getBranchVisibilityExpression())

    def _getBranchVisibilityExpression(self, branch_class=None):
        """Return the where clauses for visibility."""
        return []

    def _getCandidateBranchesWith(self):
        """Return WITH clauses defining candidate branches.

        These are defined in terms of scope_branches which should be
        separately calculated.
        """
        return [
            With("candidate_branches", SQL("SELECT id from scope_branches"))]

    def _preloadDataForBranches(self, branches):
        """Preload branches cached associated product series and
        suite source packages."""
        caches = dict((branch.id, get_property_cache(branch))
            for branch in branches)
        branch_ids = caches.keys()
        for cache in caches.values():
            if not safe_hasattr(cache, '_associatedProductSeries'):
                cache._associatedProductSeries = []
            if not safe_hasattr(cache, '_associatedSuiteSourcePackages'):
                cache._associatedSuiteSourcePackages = []
            if not safe_hasattr(cache, 'code_import'):
                cache.code_import = None
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
        links = series_set.findForBranches(branches).order_by(
            SeriesSourcePackageBranch.pocket)
        for link in links:
            cache = caches[link.branchID]
            cache._associatedSuiteSourcePackages.append(
                link.suite_sourcepackage)
        for code_import in IStore(CodeImport).find(
            CodeImport, CodeImport.branchID.is_in(branch_ids)):
            cache = caches[code_import.branchID]
            cache.code_import = code_import

    def getBranches(self, eager_load=False):
        """See `IBranchCollection`."""
        all_tables = set(
            self._tables.values() + self._asymmetric_tables.values())
        tables = [Branch] + list(all_tables)
        expressions = self._getBranchExpressions()
        resultset = self.store.using(*tables).find(Branch, *expressions)
        if not eager_load:
            return resultset

        def do_eager_load(rows):
            branch_ids = set(branch.id for branch in rows)
            if not branch_ids:
                return
            self._preloadDataForBranches(rows)
            load_related(Product, rows, ['productID'])
            # So far have only needed the persons for their canonical_url - no
            # need for validity etc in the /branches API call.
            load_related(Person, rows,
                ['ownerID', 'registrantID', 'reviewerID'])
            load_referencing(BugBranch, rows, ['branchID'])
        return DecoratedResultSet(resultset, pre_iter_hook=do_eager_load)

    def getMergeProposals(self, statuses=None, for_branches=None,
                          target_branch=None, merged_revnos=None,
                          eager_load=False):
        """See `IBranchCollection`."""
        if for_branches is not None and not for_branches:
            # We have an empty branches list, so we can shortcut.
            return EmptyResultSet()
        elif merged_revnos is not None and not merged_revnos:
            # We have an empty revnos list, so we can shortcut.
            return EmptyResultSet()
        elif (self._asymmetric_filter_expressions or
            for_branches is not None or
            target_branch is not None or
            merged_revnos is not None):
            return self._naiveGetMergeProposals(statuses, for_branches,
                target_branch, merged_revnos, eager_load)
        else:
            # When examining merge proposals in a scope, this is a moderately
            # effective set of constrained queries. It is not effective when
            # unscoped or when tight constraints on branches are present.
            return self._scopedGetMergeProposals(statuses)

    def _naiveGetMergeProposals(self, statuses=None, for_branches=None,
        target_branch=None, merged_revnos=None, eager_load=False):

        def do_eager_load(rows):
            branch_ids = set()
            person_ids = set()
            diff_ids = set()
            for mp in rows:
                branch_ids.add(mp.target_branchID)
                branch_ids.add(mp.source_branchID)
                person_ids.add(mp.registrantID)
                person_ids.add(mp.merge_reporterID)
                diff_ids.add(mp.preview_diff_id)
            if not branch_ids:
                return

            # Pre-load Person and ValidPersonCache.
            list(self.store.find(
                (Person, ValidPersonCache),
                ValidPersonCache.id == Person.id,
                Person.id.is_in(person_ids),
                ))

            # Pre-load PreviewDiffs and Diffs.
            list(self.store.find(
                (PreviewDiff, Diff),
                PreviewDiff.id.is_in(diff_ids),
                Diff.id == PreviewDiff.diff_id))

            branches = set(
                self.store.find(Branch, Branch.id.is_in(branch_ids)))
            self._preloadDataForBranches(branches)

        Target = ClassAlias(Branch, "target")
        extra_tables = list(set(
            self._tables.values() + self._asymmetric_tables.values()))
        tables = [Branch] + extra_tables + [
            Join(BranchMergeProposal, And(
                Branch.id == BranchMergeProposal.source_branchID,
                *(self._branch_filter_expressions +
                  self._asymmetric_filter_expressions))),
            Join(Target, Target.id == BranchMergeProposal.target_branchID),
            ]
        expressions = self._getBranchVisibilityExpression()
        expressions.extend(self._getBranchVisibilityExpression(Target))
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
        if statuses is not None:
            expressions.append(
                BranchMergeProposal.queue_status.is_in(statuses))
        resultset = self.store.using(*tables).find(
            BranchMergeProposal, *expressions)
        if not eager_load:
            return resultset
        else:
            return DecoratedResultSet(resultset, pre_iter_hook=do_eager_load)

    def _scopedGetMergeProposals(self, statuses):
        scope_tables = [Branch] + self._tables.values()
        scope_expressions = self._branch_filter_expressions
        select = self.store.using(*scope_tables).find(
            (Branch.id, Branch.transitively_private, Branch.ownerID),
            *scope_expressions)
        branches_query = select._get_select()
        with_expr = [With("scope_branches", branches_query)
            ] + self._getCandidateBranchesWith()
        expressions = [SQL("""
            source_branch IN (SELECT id FROM candidate_branches) AND
            target_branch IN (SELECT id FROM candidate_branches)""")]
        tables = [BranchMergeProposal]
        if self._asymmetric_filter_expressions:
            # Need to filter on Branch beyond the with constraints.
            expressions += self._asymmetric_filter_expressions
            expressions.append(
                BranchMergeProposal.source_branchID == Branch.id)
            tables.append(Branch)
            tables.extend(self._asymmetric_tables.values())
        if statuses is not None:
            expressions.append(
                BranchMergeProposal.queue_status.is_in(statuses))
        return self.store.with_(with_expr).using(*tables).find(
            BranchMergeProposal, *expressions)

    def getMergeProposalsForPerson(self, person, status=None):
        """See `IBranchCollection`."""
        # We want to limit the proposals to those where the source branch is
        # limited by the defined collection.
        owned = self.ownedBy(person).getMergeProposals(status)
        reviewing = self.getMergeProposalsForReviewer(person, status)
        resultset = owned.union(reviewing)

        def do_eager_load(rows):
            # Load the source/target branches and preload the data for
            # these branches.
            source_branches = load_related(Branch, rows, ['source_branchID'])
            target_branches = load_related(Branch, rows, ['target_branchID'])
            self._preloadDataForBranches(target_branches + source_branches)
            load_related(Product, target_branches, ['productID'])

            # Cache person's data (registrants of the proposal and
            # owners of the source branches).
            person_ids = set().union(
                (proposal.registrantID for proposal in rows),
                (branch.ownerID for branch in source_branches))
            list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
                person_ids, need_validity=True))
        return DecoratedResultSet(resultset, pre_iter_hook=do_eager_load)

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
        visibility = self._getBranchVisibilityExpression()
        if visibility:
            expressions.append(BranchMergeProposal.target_branchID.is_in(
                Select(Branch.id, visibility)))
        if status is not None:
            expressions.append(
                BranchMergeProposal.queue_status.is_in(status))
        proposals = self.store.using(*tables).find(
            BranchMergeProposal, *expressions)
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
                    filter_bugtasks_by_context(branch.target.context, tasks))

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
        return self._filterBy([Branch.owner == person], symmetric=False)

    def ownedByTeamMember(self, person):
        """See `IBranchCollection`."""
        subquery = Select(
            TeamParticipation.teamID,
            where=TeamParticipation.personID == person.id)
        filter = [In(Branch.ownerID, subquery)]

        return self._filterBy(filter, symmetric=False)

    def registeredBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.registrant == person], symmetric=False)

    def relatedTo(self, person):
        """See `IBranchCollection`."""
        return self._filterBy(
            [Branch.id.is_in(
                Union(
                    Select(Branch.id, Branch.owner == person),
                    Select(Branch.id, Branch.registrant == person),
                    Select(Branch.id,
                           And(BranchSubscription.person == person,
                               BranchSubscription.branch == Branch.id))))],
            symmetric=False)

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
                      BranchSubscription.branch == Branch.id),
            symmetric=False)

    def targetedBy(self, person, since=None):
        """See `IBranchCollection`."""
        clauses = [BranchMergeProposal.registrant == person]
        if since is not None:
            clauses.append(BranchMergeProposal.date_created >= since)
        return self._filterBy(
            clauses,
            table=BranchMergeProposal,
            join=Join(BranchMergeProposal,
                      BranchMergeProposal.target_branch == Branch.id),
            symmetric=False)

    def linkedToBugs(self, bugs):
        """See `IBranchCollection`."""
        bug_ids = [bug.id for bug in bugs]
        return self._filterBy(
            [In(BugBranch.bugID, bug_ids)],
            table=BugBranch,
            join=Join(BugBranch, BugBranch.branch == Branch.id),
            symmetric=False)

    def visibleByUser(self, person):
        """See `IBranchCollection`."""
        if (person == LAUNCHPAD_SERVICES or
            user_has_special_branch_access(person)):
            return self
        if person is None:
            return AnonymousBranchCollection(
                self._store, self._branch_filter_expressions,
                self._tables, self._exclude_from_search,
                self._asymmetric_filter_expressions, self._asymmetric_tables)
        return VisibleBranchCollection(
            person, self._store, self._branch_filter_expressions,
            self._tables, self._exclude_from_search,
            self._asymmetric_filter_expressions, self._asymmetric_tables)

    def withBranchType(self, *branch_types):
        return self._filterBy([Branch.branch_type.is_in(branch_types)],
            symmetric=False)

    def withLifecycleStatus(self, *statuses):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.lifecycle_status.is_in(statuses)],
            symmetric=False)

    def modifiedSince(self, epoch):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.date_last_modified > epoch],
            symmetric=False)

    def scannedSince(self, epoch):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.last_scanned > epoch], symmetric=False)


class AnonymousBranchCollection(GenericBranchCollection):
    """Branch collection that only shows public branches."""

    def _getBranchVisibilityExpression(self, branch_class=Branch):
        """Return the where clauses for visibility."""
        return [branch_class.transitively_private == False]

    def _getCandidateBranchesWith(self):
        """Return WITH clauses defining candidate branches.

        These are defined in terms of scope_branches which should be
        separately calculated.
        """
        # Anonymous users get public branches only.
        return [
            With("candidate_branches",
                SQL("""select id from scope_branches
                    where not transitively_private"""))
            ]


class VisibleBranchCollection(GenericBranchCollection):
    """A branch collection that has special logic for visibility."""

    def __init__(self, user, store=None, branch_filter_expressions=None,
                 tables=None, exclude_from_search=None,
                 asymmetric_filter_expressions=None, asymmetric_tables=None):
        super(VisibleBranchCollection, self).__init__(
            store=store, branch_filter_expressions=branch_filter_expressions,
            tables=tables, exclude_from_search=exclude_from_search,
            asymmetric_filter_expressions=asymmetric_filter_expressions,
            asymmetric_tables=asymmetric_tables)
        self._user = user
        self._private_branch_ids = self._getPrivateBranchSubQuery()

    def _filterBy(self, expressions, table=None, join=None,
                  exclude_from_search=None, symmetric=True):
        """Return a subset of this collection, filtered by 'expressions'.

        :param symmetric: If True this filter will apply to both sides
            of merge proposal lookups and any other lookups that join
            Branch back onto Branch.
        """
        # NOTE: JonathanLange 2009-02-17: We might be able to avoid the need
        # for explicit 'tables' by harnessing Storm's table inference system.
        # See http://paste.ubuntu.com/118711/ for one way to do that.
        if table is not None:
            if join is None:
                raise InvalidFilter("Cannot specify a table without a join.")
        if expressions is None:
            expressions = []
        tables = self._tables.copy()
        asymmetric_tables = self._asymmetric_tables.copy()
        if symmetric:
            if table is not None:
                tables[table] = join
            symmetric_expr = self._branch_filter_expressions + expressions
            asymmetric_expr = list(self._asymmetric_filter_expressions)
        else:
            if table is not None:
                asymmetric_tables[table] = join
            symmetric_expr = list(self._branch_filter_expressions)
            asymmetric_expr = (
                self._asymmetric_filter_expressions + expressions)
        if exclude_from_search is None:
            exclude_from_search = []
        return self.__class__(
            self._user,
            self.store,
            symmetric_expr,
            tables,
            self._exclude_from_search + exclude_from_search,
            asymmetric_expr,
            asymmetric_tables)

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
                       Branch.transitively_private == True)),
            # Private branches the person is subscribed to, either directly or
            # indirectly.
            Select(Branch.id,
                   And(BranchSubscription.branch == Branch.id,
                       BranchSubscription.person ==
                       TeamParticipation.teamID,
                       TeamParticipation.person == person,
                       Branch.transitively_private == True)))
        return private_branches

    def _getBranchVisibilityExpression(self, branch_class=Branch):
        """Return the where clauses for visibility.

        :param branch_class: The Branch class to use - permits using
            ClassAliases.
        """
        public_branches = branch_class.transitively_private == False
        if self._private_branch_ids is None:
            # Public only.
            return [public_branches]
        else:
            public_or_private = Or(
                public_branches,
                branch_class.id.is_in(self._private_branch_ids))
            return [public_or_private]

    def _getCandidateBranchesWith(self):
        """Return WITH clauses defining candidate branches.

        These are defined in terms of scope_branches which should be
        separately calculated.
        """
        person = self._user
        if person is None:
            # Really an anonymous sitation
            return [
                With("candidate_branches",
                    SQL("""
                        select id from scope_branches
                        where not transitively_private"""))
                ]
        return [
            With("teams", self.store.find(TeamParticipation.teamID,
                TeamParticipation.personID == person.id)._get_select()),
            With("private_branches", SQL("""
                SELECT scope_branches.id FROM scope_branches WHERE
                scope_branches.transitively_private AND (
                    (scope_branches.owner in (select team from teams) OR
                     EXISTS(SELECT true from BranchSubscription, teams WHERE
                         branchsubscription.branch = scope_branches.id AND
                         branchsubscription.person = teams.team)))""")),
            With("candidate_branches", SQL("""
                (SELECT id FROM private_branches) UNION
                (select id FROM scope_branches
                WHERE not transitively_private)"""))
            ]

    def visibleByUser(self, person):
        """See `IBranchCollection`."""
        if person == self._user:
            return self
        raise InvalidFilter(
            "Cannot filter for branches visible by user %r, already "
            "filtering for %r" % (person, self._user))
