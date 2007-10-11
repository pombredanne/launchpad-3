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

from zope.component import getUtility
from zope.interface import implements
from zope.formlib import form
from zope.schema import Choice

from canonical.config import config
from canonical.lp import decorates

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces import (
    BranchLifecycleStatus, BranchLifecycleStatusFilter, BranchListingSort,
    DEFAULT_BRANCH_STATUS_IN_LISTING, IBranch,
    IBranchSet, IBugBranchSet, IBranchBatchNavigator, IBranchListingFilter)
from canonical.launchpad.webapp import LaunchpadFormView, custom_widget
from canonical.launchpad.webapp.batching import TableBatchNavigator
from canonical.widgets import LaunchpadDropdownWidget


class BranchListingItem:
    """A decorated branch.

    Some attributes that we want to display are too convoluted or expensive
    to get on the fly for each branch in the listing.  These items are
    prefetched by the view and decorate the branch.
    """
    decorates(IBranch, 'branch')

    def __init__(self, branch, last_commit, now, bugbranches, role=None):
        self.branch = branch
        self.last_commit = last_commit
        self.bugbranches = bugbranches
        self.role = role
        self._now = now

    @property
    def elapsed_time(self):
        """How long since the branch's last commit."""
        return self.last_commit and (self._now - self.last_commit)

    @property
    def since_created(self):
        """How long since the branch was created."""
        # Need to make an TZ unaware date in order to subtract it.
        unaware_date = self.branch.date_created.replace(tzinfo=None)
        return self._now - unaware_date


class BranchListingBatchNavigator(TableBatchNavigator):
    """Batch up the branch listings."""
    implements(IBranchBatchNavigator)

    def __init__(self, view):
        TableBatchNavigator.__init__(
            self, view._branches(), view.request,
            columns_to_show=view.extra_columns,
            size=config.launchpad.branchlisting_batch_size)
        self.view = view
        self.column_count = 4 + len(view.extra_columns)
        self._now = datetime.utcnow()

    @cachedproperty
    def last_commit(self):
        """Get the last commit times for the current batch."""
        return getUtility(IBranchSet).getLastCommitForBranches(
            self.currentBatch())

    @cachedproperty
    def branch_bug_links(self):
        """Get all bugs associated the with current batch."""
        bugbranches = getUtility(IBugBranchSet).getBugBranchesForBranches(
            self.batch)
        result = {}
        for bugbranch in bugbranches:
            result.setdefault(
                bugbranch.branch.id, []).append(bugbranch)
        return result

    def _createItem(self, branch):
        last_commit = self.last_commit[branch]
        bug_branches = self.branch_bug_links.get(branch.id)
        role = self.view.roleForBranch(branch)
        return BranchListingItem(
            branch, last_commit, self._now, bug_branches, role)

    def branches(self):
        "Return a list of BranchListingItems"
        return [self._createItem(branch) for branch in self.currentBatch()]

    @cachedproperty
    def multiple_pages(self):
        return self.batch.total() > self.batch.size

    @property
    def table_class(self):
        if self.multiple_pages:
            return "listing"
        else:
            return "listing sortable"


class BranchListingView(LaunchpadFormView):
    """A base class for views of branch listings."""
    schema = IBranchListingFilter
    field_names = ['lifecycle', 'sort_by']
    custom_widget('lifecycle', LaunchpadDropdownWidget)
    custom_widget('sort_by', LaunchpadDropdownWidget)
    extra_columns = []
    title_prefix = 'Bazaar'
    no_sort_by = []

    @property
    def page_title(self):
        return '%s branches for %s' % (
            self.title_prefix, self.context.displayname)

    @property
    def initial_values(self):
        return {
            'lifecycle': BranchLifecycleStatusFilter.CURRENT
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

    def roleForBranch(self, branch):
        """Overridden by derived classes to display something in
        the role column if the role column is visible."""
        return None

    @property
    def no_branch_message(self):
        """This may also be overridden in derived classes to provide
        context relevant messages if there are no branches returned."""
        if self.selected_lifecycle_status is not None:
            message = (
                'There may be branches related to %s '
                'but none of them match the current filter criteria '
                'for this page. Try filtering on "Any Status".')
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
        vocab_items = BranchListingSort.items.items[:]
        for item in self.no_sort_by:
            vocab_items.remove(item)
        lifecycle_field = IBranchListingFilter['lifecycle']
        name = self.prefix + '.' + lifecycle_field.__name__
        form_value = self.request.form.get(name)
        if form_value is not None:
            status_filter = BranchLifecycleStatusFilter.getTermByToken(
                form_value).value
            if status_filter not in (BranchLifecycleStatusFilter.ALL,
                                     BranchLifecycleStatusFilter.CURRENT):
                vocab_items.remove(BranchListingSort.LIFECYCLE)
        return vocab_items

    @property
    def sort_by_field(self):
        orig_field = IBranchListingFilter['sort_by']
        values = self.branch_listing_sort_values
        return Choice(__name__=orig_field.__name__,
                      title=orig_field.title,
                      required=True, values=values, default=values[0])

    def setUpWidgets(self, context=None):
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

    def _branches(self):
        """Return the branches ordered by date created."""
        return getUtility(IBranchSet).getRecentlyRegisteredBranches(
            lifecycle_statuses=self.selected_lifecycle_status,
            visible_by_user=self.user)


class RecentlyImportedBranchesView(NoContextBranchListingView):
    """A batched view of imported branches ordered by last scanned time."""

    page_title = 'Recently imported branches'
    extra_columns = ('product', 'date_created')

    def _branches(self):
        """Return imported branches ordered by last update."""
        return getUtility(IBranchSet).getRecentlyImportedBranches(
            lifecycle_statuses=self.selected_lifecycle_status,
            visible_by_user=self.user)


class RecentlyChangedBranchesView(NoContextBranchListingView):
    """A batched view of non-imported branches ordered by last scanned time."""

    page_title = 'Recently changed branches'

    def _branches(self):
        """Return non-imported branches orded by last commit."""
        return getUtility(IBranchSet).getRecentlyChangedBranches(
            lifecycle_statuses=self.selected_lifecycle_status,
            visible_by_user=self.user)
