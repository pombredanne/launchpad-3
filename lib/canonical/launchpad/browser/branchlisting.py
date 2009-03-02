# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Base class view for branch listings."""

__metaclass__ = type

__all__ = [
    'BranchListingView',
    'RecentlyChangedBranchesView',
    'RecentlyImportedBranchesView',
    'RecentlyRegisteredBranchesView',
    ]

from datetime import datetime

import pytz
from zope.component import getUtility
from zope.interface import implements
from zope.formlib import form
from zope.schema import Choice

from canonical.config import config

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.browser.branch import BranchBadges
from canonical.launchpad.browser.feeds import (
    FeedsMixin, PersonBranchesFeedLink, PersonRevisionsFeedLink,
    ProductBranchesFeedLink, ProductRevisionsFeedLink,
    ProjectBranchesFeedLink, ProjectRevisionsFeedLink)
from canonical.launchpad.interfaces import (
    bazaar_identity,
    BranchLifecycleStatus,
    BranchLifecycleStatusFilter,
    DEFAULT_BRANCH_STATUS_IN_LISTING,
    IBranch,
    IBranchBatchNavigator,
    IBranchListingFilter,
    IBugBranchSet,
    IProductSeriesSet,
    IRevisionSet,
    ISpecificationBranchSet)
from canonical.launchpad.interfaces.branch import (
    BranchListingSort, BranchPersonSearchContext,
    BranchPersonSearchRestriction, IBranchSet)
from canonical.launchpad.interfaces.branchmergeproposal import (
    BranchMergeProposalStatus, IBranchMergeProposalGetter)
from canonical.launchpad.interfaces.distroseries import DistroSeriesStatus
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.webapp import (
    ApplicationMenu, canonical_url, custom_widget, LaunchpadFormView, Link)
from canonical.launchpad.webapp.batching import TableBatchNavigator
from canonical.launchpad.webapp.publisher import LaunchpadView
from canonical.widgets import LaunchpadDropdownWidget
from lazr.delegates import delegates


class BranchListingItem(BranchBadges):
    """A decorated branch.

    Some attributes that we want to display are too convoluted or expensive
    to get on the fly for each branch in the listing.  These items are
    prefetched by the view and decorate the branch.
    """
    delegates(IBranch, 'context')

    def __init__(self, branch, last_commit, now, show_bug_badge,
                 show_blueprint_badge, is_dev_focus,
                 associated_product_series):
        BranchBadges.__init__(self, branch)
        self.last_commit = last_commit
        self.show_bug_badge = show_bug_badge
        self.show_blueprint_badge = show_blueprint_badge
        self._now = now
        self.is_development_focus = is_dev_focus
        self.associated_product_series = associated_product_series

    @property
    def active_series(self):
        return [series for series in self.associated_product_series
                if series.status != DistroSeriesStatus.OBSOLETE]

    @property
    def bzr_identity(self):
        """Produce the bzr identity from our known associated series."""
        return bazaar_identity(
            self.context, self.associated_product_series,
            self.is_development_focus)

    @property
    def since_updated(self):
        """How long since the branch was last updated."""
        return self._now - self.context.date_last_modified

    @property
    def since_created(self):
        """How long since the branch was created."""
        return self._now - self.context.date_created

    def isBugBadgeVisible(self):
        return self.show_bug_badge

    def isBlueprintBadgeVisible(self):
        return self.show_blueprint_badge

    @property
    def revision_author(self):
        return self.last_commit.revision_author

    @property
    def revision_number(self):
        return self.context.revision_count

    @property
    def revision_log(self):
        return self.last_commit.log_body

    @property
    def revision_date(self):
        return self.last_commit.revision_date

    @property
    def revision_codebrowse_link(self):
        return self.context.codebrowse_url(
            'revision', str(self.context.revision_count))


class BranchListingBatchNavigator(TableBatchNavigator):
    """Batch up the branch listings."""
    implements(IBranchBatchNavigator)

    def __init__(self, view):
        TableBatchNavigator.__init__(
            self, view.getVisibleBranchesForUser(), view.request,
            columns_to_show=view.extra_columns,
            size=config.launchpad.branchlisting_batch_size)
        self.view = view
        self.column_count = 4 + len(view.extra_columns)
        self._now = datetime.now(pytz.UTC)
        self._dev_series_map = {}

    @cachedproperty
    def _branches_for_current_batch(self):
        return list(self.currentBatch())

    @cachedproperty
    def has_bug_branch_links(self):
        """Return a set of branch ids that should show bug badges."""
        bug_branches = getUtility(IBugBranchSet).getBugBranchesForBranches(
            self._branches_for_current_batch, self.view.user)
        result = set()
        for bug_branch in bug_branches:
            result.add(bug_branch.branch.id)
        return result

    @cachedproperty
    def has_branch_spec_links(self):
        """Return a set of branch ids that should show blueprint badges."""
        spec_branches = getUtility(
            ISpecificationBranchSet).getSpecificationBranchesForBranches(
            self._branches_for_current_batch, self.view.user)
        result = set()
        for spec_branch in spec_branches:
            result.add(spec_branch.branch.id)
        return result

    @cachedproperty
    def tip_revisions(self):
        """Return a set of branch ids that should show blueprint badges."""
        revisions = getUtility(IRevisionSet).getTipRevisionsForBranches(
            self._branches_for_current_batch)
        if revisions is None:
            revision_map = {}
        else:
            # Key the revisions by revision id.
            revision_map = dict((revision.revision_id, revision)
                                for revision in revisions)
        # Return a dict keyed on branch id.
        return dict((branch.id, revision_map.get(branch.last_scanned_id))
                     for branch in self._branches_for_current_batch)

    @cachedproperty
    def product_series_map(self):
        """Return a map of branch id to a list of product series."""
        series_resultset = getUtility(IProductSeriesSet).getSeriesForBranches(
            self._branches_for_current_batch)
        result = {}
        for series in series_resultset:
            result.setdefault(series.series_branch.id, []).append(series)
        return result

    def getProductSeries(self, branch):
        """Get the associated product series for the branch.

        If the branch has more than one associated product series
        they are listed in alphabetical order, unless one of them is
        the current development focus, in which case that comes first.
        """
        series = self.product_series_map.get(branch.id, [])
        if len(series) > 1:
            # Check for development focus.
            dev_focus = branch.product.development_focus
            if dev_focus is not None and dev_focus in series:
                series.remove(dev_focus)
                series.insert(0, dev_focus)
        return series

    def getDevFocusBranch(self, branch):
        """Get the development focus branch that relates to `branch`."""
        if branch.product is None:
            return None
        try:
            return self._dev_series_map[branch.product]
        except KeyError:
            result = branch.product.development_focus.series_branch
            self._dev_series_map[branch.product] = result
            return result

    def _createItem(self, branch):
        last_commit = self.tip_revisions[branch.id]
        show_bug_badge = branch.id in self.has_bug_branch_links
        show_blueprint_badge = branch.id in self.has_branch_spec_links
        associated_product_series = self.getProductSeries(branch)
        is_dev_focus = (self.getDevFocusBranch(branch) == branch)
        return BranchListingItem(
            branch, last_commit, self._now, show_bug_badge,
            show_blueprint_badge, is_dev_focus, associated_product_series)

    def branches(self):
        """Return a list of BranchListingItems."""
        return [self._createItem(branch)
                for branch in self._branches_for_current_batch]

    @cachedproperty
    def multiple_pages(self):
        return self.batch.total() > self.batch.size

    @property
    def table_class(self):
        # XXX: MichaelHudson 2007-10-18 bug=153894: This means there are two
        # ways of sorting a one-page branch listing, which is a confusing and
        # incoherent.
        if self.multiple_pages:
            return "listing"
        else:
            return "listing sortable"


class BranchListingView(LaunchpadFormView, FeedsMixin):
    """A base class for views of branch listings."""
    schema = IBranchListingFilter
    field_names = ['lifecycle', 'sort_by']
    development_focus_branch = None
    show_set_development_focus = False
    custom_widget('lifecycle', LaunchpadDropdownWidget)
    custom_widget('sort_by', LaunchpadDropdownWidget)
    # Showing the series links is only really useful on product listing
    # pages.  Derived views can override this value to have the series links
    # shown in the branch listings.
    show_series_links = False
    extra_columns = []
    heading_template = 'Bazaar branches for %(displayname)s'
    # no_sort_by is a sequence of items from the BranchListingSort
    # enumeration to not offer in the sort_by widget.
    no_sort_by = ()

    # Set the feed types to be only the various branches feed links.  The
    # `feed_links` property will screen this list and produce only the feeds
    # appropriate to the context.
    feed_types = (
        ProjectBranchesFeedLink,
        ProjectRevisionsFeedLink,
        ProductBranchesFeedLink,
        ProductRevisionsFeedLink,
        PersonBranchesFeedLink,
        PersonRevisionsFeedLink,
        )

    @property
    def heading(self):
        return self.heading_template % {
            'displayname': self.context.displayname}

    @property
    def initial_values(self):
        return {
            'lifecycle': BranchLifecycleStatusFilter.CURRENT,
            }

    @cachedproperty
    def selected_lifecycle_status(self):
        widget = self.widgets['lifecycle']

        if widget.hasValidInput():
            lifecycle_filter = widget.getInputValue()
        else:
            lifecycle_filter = BranchLifecycleStatusFilter.CURRENT

        if lifecycle_filter == BranchLifecycleStatusFilter.ALL:
            return None
        elif lifecycle_filter == BranchLifecycleStatusFilter.CURRENT:
            return DEFAULT_BRANCH_STATUS_IN_LISTING
        else:
            return (BranchLifecycleStatus.items[lifecycle_filter.name], )

    def branches(self):
        """All branches related to this target, sorted for display."""
        # Separate the public property from the underlying virtual method.
        return BranchListingBatchNavigator(self)

    def getVisibleBranchesForUser(self):
        """Get branches visible to the user.

        This method is called from the `BranchListingBatchNavigator` to
        get the branches to show in the listing.
        """
        return self._branches(self.selected_lifecycle_status)

    def hasAnyBranchesVisibleByUser(self):
        """Does the context have any branches that are visible to the user?"""
        return self._branches(None).count() > 0

    @property
    def branch_search_context(self):
        """The context used for the branch search."""
        return self.context

    def _branches(self, lifecycle_status):
        """Return a sequence of branches.

        This method is overridden in the derived classes to perform the
        specific query.

        :param lifecycle_status: A filter of the branch's lifecycle status.
        """
        return getUtility(IBranchSet).getBranchesForContext(
            self.branch_search_context, lifecycle_status, self.user,
            self.sort_by)

    @property
    def no_branch_message(self):
        """This may also be overridden in derived classes to provide
        context relevant messages if there are no branches returned."""
        if (self.selected_lifecycle_status is not None
            and self.hasAnyBranchesVisibleByUser()):
            message = (
                'There are branches related to %s but none of them match the '
                'current filter criteria for this page. '
                'Try filtering on "Any Status".')
        else:
            message = (
                'There are no branches related to %s '
                'in Launchpad today. You can use Launchpad as a registry for '
                'Bazaar branches, and encourage broader community '
                'participation in your project using '
                'distributed version control.')
        return message % self.context.displayname

    @property
    def branch_listing_sort_values(self):
        """The enum items we should present in the 'sort_by' widget.

        Subclasses get the chance to avoid some sort options (it makes no
        sense to offer to sort the product branch listing by product name!)
        and if we're filtering to a single lifecycle status it doesn't make
        much sense to sort by lifecycle.
        """
        # This is pretty painful.
        # First we find the items which are not excluded for this view.
        vocab_items = [item for item in BranchListingSort.items.items
                       if item not in self.no_sort_by]
        # Finding the value of the lifecycle_filter widget is awkward as we do
        # this when the widgets are being set up.  We go digging in the
        # request.
        lifecycle_field = IBranchListingFilter['lifecycle']
        name = self.prefix + '.' + lifecycle_field.__name__
        form_value = self.request.form.get(name)
        if form_value is not None:
            try:
                status_filter = BranchLifecycleStatusFilter.getTermByToken(
                    form_value).value
            except LookupError:
                # We explicitly support bogus values in field.lifecycle --
                # they are treated the same as "CURRENT", which includes more
                # than one lifecycle.
                pass
            else:
                if status_filter not in (BranchLifecycleStatusFilter.ALL,
                                         BranchLifecycleStatusFilter.CURRENT):
                    vocab_items.remove(BranchListingSort.LIFECYCLE)
        return vocab_items

    @property
    def sort_by_field(self):
        """The zope.schema field for the 'sort_by' widget."""
        orig_field = IBranchListingFilter['sort_by']
        values = self.branch_listing_sort_values
        return Choice(__name__=orig_field.__name__,
                      title=orig_field.title,
                      required=True, values=values, default=values[0])

    @property
    def sort_by(self):
        """The value of the `sort_by` widget, or None if none was present."""
        widget = self.widgets['sort_by']
        if widget.hasValidInput():
            return widget.getInputValue()
        else:
            return None

    def setUpWidgets(self, context=None):
        """Set up the 'sort_by' widget with only the applicable choices."""
        fields = []
        for field_name in self.field_names:
            if field_name == 'sort_by':
                field = form.FormField(self.sort_by_field)
            else:
                field = self.form_fields[field_name]
            fields.append(field)
        self.form_fields = form.Fields(*fields)
        super(BranchListingView, self).setUpWidgets(context)


class NoContextBranchListingView(BranchListingView):
    """A branch listing that has no associated product or person."""

    field_names = ['lifecycle']
    no_sort_by = (BranchListingSort.DEFAULT,)

    no_branch_message = (
        'There are no branches that match the current status filter.')
    extra_columns = ('author', 'product', 'date_created')


class RecentlyRegisteredBranchesView(NoContextBranchListingView):
    """A batched view of branches orded by registration date."""

    page_title = 'Recently registered branches'

    def _branches(self, lifecycle_status):
        """Return the branches ordered by date created."""
        return getUtility(IBranchSet).getRecentlyRegisteredBranches(
            lifecycle_statuses=lifecycle_status,
            visible_by_user=self.user)


class RecentlyImportedBranchesView(NoContextBranchListingView):
    """A batched view of imported branches ordered by last scanned time."""

    page_title = 'Recently imported branches'
    extra_columns = ('product', 'date_created')

    def _branches(self, lifecycle_status):
        """Return imported branches ordered by last update."""
        return getUtility(IBranchSet).getRecentlyImportedBranches(
            lifecycle_statuses=lifecycle_status,
            visible_by_user=self.user)


class RecentlyChangedBranchesView(NoContextBranchListingView):
    """Batched view of non-imported branches ordered by last scanned time."""

    page_title = 'Recently changed branches'

    def _branches(self, lifecycle_status):
        """Return non-imported branches orded by last commit."""
        return getUtility(IBranchSet).getRecentlyChangedBranches(
            lifecycle_statuses=lifecycle_status,
            visible_by_user=self.user)


class PersonBranchCountMixin:
    """A mixin class for person branch listings."""

    @cachedproperty
    def total_branch_count(self):
        """Return the number of branches related to the person."""
        query = getUtility(IBranchSet).getBranchesForContext(
            self.context, visible_by_user=self.user)
        return query.count()

    @cachedproperty
    def registered_branch_count(self):
        """Return the number of branches registered by the person."""
        query = getUtility(IBranchSet).getBranchesForContext(
            BranchPersonSearchContext(
                self.context, BranchPersonSearchRestriction.REGISTERED),
            visible_by_user=self.user)
        return query.count()

    @cachedproperty
    def owned_branch_count(self):
        """Return the number of branches owned by the person."""
        query = getUtility(IBranchSet).getBranchesForContext(
            BranchPersonSearchContext(
                self.context, BranchPersonSearchRestriction.OWNED),
            visible_by_user=self.user)
        return query.count()

    @cachedproperty
    def subscribed_branch_count(self):
        """Return the number of branches subscribed to by the person."""
        query = getUtility(IBranchSet).getBranchesForContext(
            BranchPersonSearchContext(
                self.context, BranchPersonSearchRestriction.SUBSCRIBED),
            visible_by_user=self.user)
        return query.count()

    @property
    def user_in_context_team(self):
        if self.user is None:
            return False
        return self.user.inTeam(self.context)

    @cachedproperty
    def active_review_count(self):
        """Return the number of active reviews for the user."""
        query = getUtility(IBranchMergeProposalGetter).getProposalsForContext(
            self.context, [BranchMergeProposalStatus.NEEDS_REVIEW], self.user)
        return query.count()

    @cachedproperty
    def approved_merge_count(self):
        """Return the number of active reviews for the user."""
        query = getUtility(IBranchMergeProposalGetter).getProposalsForContext(
            self.context, [BranchMergeProposalStatus.CODE_APPROVED],
            self.user)
        return query.count()

    @cachedproperty
    def requested_review_count(self):
        """Return the number of active reviews for the user."""
        utility = getUtility(IBranchMergeProposalGetter)
        query = utility.getProposalsForReviewer(
            self.context, [
                BranchMergeProposalStatus.CODE_APPROVED,
                BranchMergeProposalStatus.NEEDS_REVIEW],
            self.user)
        return query.count()


class PersonBranchesMenu(ApplicationMenu, PersonBranchCountMixin):

    usedfor = IPerson
    facet = 'branches'
    links = ['all_related', 'registered', 'owned', 'subscribed', 'addbranch',
             'active_reviews', 'approved_merges', 'requested_reviews']

    def all_related(self):
        return Link(canonical_url(self.context, rootsite='code'),
                    'Related branches')

    def owned(self):
        return Link('+ownedbranches', 'owned')

    def registered(self):
        return Link('+registeredbranches', 'registered')

    def subscribed(self):
        return Link('+subscribedbranches', 'subscribed')

    def active_reviews(self):
        if self.active_review_count == 1:
            text = 'active proposal'
        else:
            text = 'active proposals'
        if self.user == self.context:
            summary = 'Proposals I have submitted'
        else:
            summary = 'Proposals %s has submitted' % self.context.displayname
        return Link('+activereviews', text, summary=summary)

    def approved_merges(self):
        if self.approved_merge_count == 1:
            text = 'approved merge'
        else:
            text = 'approved merges'
        return Link('+approvedmerges', text)

    def addbranch(self):
        if self.user is None:
            enabled = False
        else:
            enabled = self.user.inTeam(self.context)
        text = 'Register branch'
        return Link('+addbranch', text, icon='add', enabled=enabled)

    def requested_reviews(self):
        if self.requested_review_count == 1:
            text = 'requested review'
        else:
            text = 'requested reviews'
        if self.user == self.context:
            summary = 'Proposals I am reviewing'
        else:
            summary = 'Proposals %s is reviewing' % self.context.displayname
        return Link('+requestedreviews', text, summary=summary)


class PersonBranchesView(BranchListingView, PersonBranchCountMixin):
    """View for branch listing for a person."""

    no_sort_by = (BranchListingSort.DEFAULT,)
    heading_template = 'Bazaar branches related to %(displayname)s'


class PersonRegisteredBranchesView(BranchListingView, PersonBranchCountMixin):
    """View for branch listing for a person's registered branches."""

    heading_template = 'Bazaar branches registered by %(displayname)s'
    no_sort_by = (BranchListingSort.DEFAULT, BranchListingSort.REGISTRANT)

    @property
    def branch_search_context(self):
        """See `BranchListingView`."""
        return BranchPersonSearchContext(
            self.context, BranchPersonSearchRestriction.REGISTERED)


class PersonOwnedBranchesView(BranchListingView, PersonBranchCountMixin):
    """View for branch listing for a person's owned branches."""

    heading_template = 'Bazaar branches owned by %(displayname)s'
    no_sort_by = (BranchListingSort.DEFAULT, BranchListingSort.REGISTRANT)

    @property
    def branch_search_context(self):
        """See `BranchListingView`."""
        return BranchPersonSearchContext(
            self.context, BranchPersonSearchRestriction.OWNED)


class PersonSubscribedBranchesView(BranchListingView, PersonBranchCountMixin):
    """View for branch listing for a person's subscribed branches."""

    heading_template = 'Bazaar branches subscribed to by %(displayname)s'
    no_sort_by = (BranchListingSort.DEFAULT,)

    @property
    def branch_search_context(self):
        """See `BranchListingView`."""
        return BranchPersonSearchContext(
            self.context, BranchPersonSearchRestriction.SUBSCRIBED)


class PersonTeamBranchesView(LaunchpadView):
    """View for team branches portlet."""

    @cachedproperty
    def teams_with_branches(self):
        def team_has_branches(team):
            branches = getUtility(IBranchSet).getBranchesForContext(
                team, visible_by_user=self.user)
            return branches.count() > 0
        return [team for team in self.context.teams_participated_in
                if team_has_branches(team) and team != self.context]


class PersonCodeSummaryView(LaunchpadView, PersonBranchCountMixin):
    """A view to render the code page summary for a person."""

    __used_for__ = IPerson

    @property
    def show_summary(self):
        """Right now we show the summary if the person has branches.

        When we add support for reviews commented on, we'll want to add
        support for showing the summary even if there are no branches.
        """
        return self.total_branch_count or self.requested_review_count
