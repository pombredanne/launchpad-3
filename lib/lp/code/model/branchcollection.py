# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Implementations of `IBranchCollection`."""

__metaclass__ = type
__all__ = [
    'GenericBranchCollection',
    ]

from storm.expr import And, Desc, LeftJoin, Join, Or, Select, Union

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet)
from lp.code.model.branch import Branch
from lp.code.model.branchmergeproposal import (
    BranchMergeProposal)
from lp.code.model.branchsubscription import BranchSubscription
from lp.code.model.codereviewcomment import CodeReviewComment
from lp.code.model.codereviewvote import (
    CodeReviewVoteReference)
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.person import Owner
from lp.registry.model.product import Product
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.registry.model.teammembership import TeamParticipation
from lp.code.interfaces.branch import (
    user_has_special_branch_access)
from lp.code.interfaces.branchcollection import (
    IBranchCollection, InvalidFilter)
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.code.interfaces.codehosting import LAUNCHPAD_SERVICES
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.launchpad.webapp.vocabulary import CountableIterator


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
        return self.getBranches(False, False).count()

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
        # XXX: JonathanLange 2009-03-04 bug=337494: getBranches() returns a
        # decorated set, so we get at the underlying set so we can get at the
        # private and juicy _get_select.
        select = self.getBranches(False, False).result_set._get_select()
        select.columns = (Branch.id,)
        return select

    def _getBranchExpressions(self):
        """Return the where expressions for this collection."""
        return self._branch_filter_expressions

    def getBranches(self, join_owner=True, join_product=True):
        """See `IBranchCollection`."""
        tables = [Branch] + self._tables.values()
        if join_owner and Owner not in self._tables:
            tables.append(Join(Owner, Branch.owner == Owner.id))
        if join_product and Product not in self._tables:
            tables.append(LeftJoin(Product, Branch.product == Product.id))
        expressions = self._getBranchExpressions()
        results = self.store.using(*tables).find(Branch, *expressions)
        # XXX TimPenhey 2008-03-16 bug 343313
        # Remove the default ordering on the Branch table.
        results = results.order_by()
        def identity(x):
            return x
        # Decorate the result set to work around bug 217644.
        return DecoratedResultSet(results, identity)

    def getMergeProposals(self, statuses=None, for_branches=None):
        """See `IBranchCollection`."""
        expressions = [
            BranchMergeProposal.source_branchID.is_in(
                self._getBranchIdQuery()),
            ]
        if for_branches is not None:
            branch_ids = [branch.id for branch in for_branches]
            expressions.append(
                BranchMergeProposal.source_branchID.is_in(branch_ids))
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

    def inSourcePackage(self, source_package):
        """See `IBranchCollection`."""
        return self._filterBy([
            Branch.distroseries == source_package.distroseries,
            Branch.sourcepackagename == source_package.sourcepackagename])

    def ownedBy(self, person):
        """See `IBranchCollection`."""
        return self._filterBy([Branch.owner == person])

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
        # XXX: JonathanLange 2009-02-23: This matches the old search algorithm
        # that used to live in vocabularies/dbojects.py. It's not actually
        # very good -- really it should match based on substrings of the
        # unique name and sort based on relevance.
        branch = self._getExactMatch(search_term)
        if branch is not None:
            if branch in self.getBranches(False, False):
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
        results = collection.getBranches().order_by(Branch.name, Branch.id)
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
        self._user_visibility_expression = self._getVisibilityExpression()

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

    def _getVisibilityExpression(self):
        # Everyone can see public branches.
        person = self._user
        public_branches = Select(Branch.id, Branch.private == False)

        if person is None:
            # Anonymous users can only see the public branches.
            visible_branches = public_branches
        else:
            # A union is used here rather than the more simplistic simple
            # joins due to the query plans generated.  If we just have a
            # simple query then we are joining across TeamParticipation and
            # BranchSubscription.  This creates a bad plan, hence the use of a
            # union.
            visible_branches = Union(
                public_branches,
                # Branches the person owns (or a team the person is in).
                Select(Branch.id,
                       And(Branch.owner == TeamParticipation.teamID,
                           TeamParticipation.person == person)),
                # Private branches the person is subscribed to, either
                # directly or indirectly.
                Select(Branch.id,
                       And(BranchSubscription.branch == Branch.id,
                           BranchSubscription.person ==
                               TeamParticipation.teamID,
                           TeamParticipation.person == person,
                           Branch.private == True)))
        return visible_branches

    def _getBranchExpressions(self):
        """Return the where expressions for this collection."""
        return self._branch_filter_expressions + [
            Branch.id.is_in(self._user_visibility_expression)]

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
        return [
            BranchMergeProposal.target_branchID.is_in(
                self._user_visibility_expression)]
