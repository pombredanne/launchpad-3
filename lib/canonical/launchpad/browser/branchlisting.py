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
    FeedsMixin, PersonBranchesFeedLink, ProductBranchesFeedLink,
    ProjectBranchesFeedLink)
from canonical.launchpad.interfaces import (
    BranchLifecycleStatus,
    BranchLifecycleStatusFilter,
    BranchListingSort,
    DEFAULT_BRANCH_STATUS_IN_LISTING,
    IBranch,
    IBranchSet,
    IBranchBatchNavigator,
    IBranchListingFilter,
    IBugBranchSet,
    IProductSeriesSet,
    IRevisionSet,
    ISpecificationBranchSet)
from canonical.launchpad.webapp import LaunchpadFormView, custom_widget
from canonical.launchpad.webapp.batching import TableBatchNavigator
from canonical.lazr import decorates
from canonical.widgets import LaunchpadDropdownWidget


class BranchListingItem(BranchBadges):
    """A decorated branch.

    Some attributes that we want to display are too convoluted or expensive
    to get on the fly for each branch in the listing.  These items are
    prefetched by the view and decorate the branch.
    """
    decorates(IBranch, 'context')

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
        return "%(codebrowse_root)s%(branch)s/revision/%(rev_no)s" % {
            'codebrowse_root': config.codehosting.codebrowse_root,
            'branch': self.context.unique_name,
            'rev_no': self.context.revision_count}


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

    def _createItem(self, branch):
        last_commit = self.tip_revisions[branch.id]
        show_bug_badge = branch.id in self.has_bug_branch_links
        show_blueprint_badge = branch.id in self.has_branch_spec_links
        associated_product_series = self.getProductSeries(branch)
        # XXX thumper 2007-11-14
        # We can't do equality checks here due to BranchWithSortKeys
        # being constructed from the BranchSet queries, and the development
        # focus branch being an actual Branch instance.
        if self.view.development_focus_branch is None:
            is_dev_focus = False
        else:
            is_dev_focus = (
                branch.id == self.view.development_focus_branch.id)
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
    custom_widget('lifecycle', LaunchpadDropdownWidget)
    custom_widget('sort_by', LaunchpadDropdownWidget)
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
        ProductBranchesFeedLink,
        PersonBranchesFeedLink,
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

    def _branches(self, lifecycle_status):
        """Return a sequence of branches.

        This method is overridden in the derived classes to perform the
        specific query.

        :param lifecycle_status: A filter of the branch's lifecycle status.
        """
        raise NotImplementedError("Derived classes must implement _branches.")

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
                field = form.FormField(
                    self.sort_by_field,
                    custom_widget=self.custom_widgets[field_name])
            else:
                field = self.form_fields[field_name]
            fields.append(field)
        self.form_fields = form.Fields(*fields)
        super(BranchListingView, self).setUpWidgets(context)


class NoContextBranchListingView(BranchListingView):
    """A branch listing that has no associated product or person."""

    field_names = ['lifecycle']

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
