# Copyright 2005 Canonical Ltd.  All rights reserved.

"""IBranchTarget browser views."""

__metaclass__ = type

__all__ = [
    'BranchTargetView',
    'PersonBranchesView',
    ]

import operator

from zope.component import getUtility

from canonical.lp import decorates
from canonical.lp.dbschema import (BranchLifecycleStatus,
                                   BranchLifecycleStatusFilter)

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces import (
    IBranch, IBranchLifecycleFilter, IBranchSet, IBugBranchSet,
    IPerson, IProduct)
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
    IBranchLifecycleFilter, IBranchSet, IPerson, IProduct)
from canonical.launchpad.webapp import LaunchpadFormView, custom_widget
from canonical.widgets import LaunchpadDropdownWidget


class BranchListingItem:
    """A decorated branch.

    Some attributes that we want to display are too convoluted or expensive
    to get on the fly for each branch in the listing.  These items are
    prefetched by the view and decorate the branch.
    """
    decorates(IBranch, 'branch')

    def __init__(self, branch, last_commit, bugbranches, role=None):
        self.branch = branch
        self.last_commit = last_commit
        self.bugbranches = bugbranches
        self.role = role
        

class BranchTargetView(LaunchpadFormView):
    schema = IBranchLifecycleFilter
    field_names = ['lifecycle']
    custom_widget('lifecycle', LaunchpadDropdownWidget)

    # The default set of statuses to show.
    CURRENT_SET = set([BranchLifecycleStatus.NEW,
                       BranchLifecycleStatus.EXPERIMENTAL,
                       BranchLifecycleStatus.DEVELOPMENT,
                       BranchLifecycleStatus.MATURE])
                  
    @property
    def initial_values(self):
        return {
            'lifecycle': BranchLifecycleStatusFilter.CURRENT
            }

    def initialize(self):
        LaunchpadFormView.initialize(self)
        self.last_commit = getUtility(IBranchSet).getLastCommitForBranches(
            self.visible_branches)

    @cachedproperty
    def branches(self):
        """All branches related to this target, sorted for display."""
        # Separate the public property from the underlying virtual method.
        return self._branches()

    def _branches(self):
        branches = self.context.branches
        items = shortlist(branches, 1000, hardlimit=1500)
        return sorted(items, key=operator.attrgetter('sort_key'))

    @cachedproperty
    def branch_bug_links(self):
        """Get all bugs associated the with visible branches."""
        bugbranches = getUtility(IBugBranchSet).getBugBranchesForBranches(
            self.visible_branches)
        result = {}
        for bugbranch in bugbranches:
            result.setdefault(
                bugbranch.branch.id, []).append(bugbranch)
        return result

    @cachedproperty
    def visible_branches(self):
        """The branches that should be visible to the user."""
        widget = self.widgets['lifecycle']

        if widget.hasValidInput():
            lifecycle_filter = widget.getInputValue()
        else:
            lifecycle_filter = BranchLifecycleStatusFilter.CURRENT

        if lifecycle_filter == BranchLifecycleStatusFilter.ALL:
            branches = self.branches
        elif lifecycle_filter == BranchLifecycleStatusFilter.CURRENT:
            branches = [branch for branch in self.branches
                        if branch.lifecycle_status in self.CURRENT_SET]
        else:
            # BranchLifecycleStatus and BranchLifecycleStatusFilter
            # share values for common elements, so to get the correct
            # status to compare against, we know that we can just
            # index into the enumeration with the value.
            show_status = BranchLifecycleStatus.items[lifecycle_filter.value]
            branches = [branch for branch in self.branches
                        if branch.lifecycle_status == show_status]
        return sorted(branches, key=operator.attrgetter('sort_key'))

    def getListingItems(self):
        """Return a list of decorated branches for easy TAL access."""
        return [BranchListingItem(branch,
                                  self.last_commit[branch],
                                  self.branch_bug_links.get(branch.id, None))
                for branch in self.visible_branches]

    def context_relationship(self):
        """The relationship text used for display.

        Explains how the this branch listing relates to the context object. 
        """
        if self.in_product_context():
            return "registered for"
        url = self.request.getURL()
        if '+authoredbranches' in url:
            return "authored by"
        elif '+registeredbranches' in url:
            return "registered but not authored by"
        elif '+subscribedbranches' in url:
            return "subscribed to by"
        else:
            return "related to"

    def in_person_context(self):
        """Whether the context object is a person."""
        return IPerson.providedBy(self.context)

    def in_product_context(self):
        """Whether the context object is a product."""
        return IProduct.providedBy(self.context)

    def categories(self):
        """This organises the branches related to this target by
        "category", where a category corresponds to a particular branch
        status. It also determines the order of those categories, and the
        order of the branches inside each category. This is used for the
        +branches view.

        It is also used in IPerson, which is not an IBranchTarget but
        which does have a IPerson.branches. In this case, it will also
        detect which set of branches you want to see. The options are:

         - all branches (self.branches)
         - authored by this person (self.context.authored_branches)
         - registered by this person (self.context.registered_branches)
         - subscribed by this person (self.context.subscribed_branches)
        """
        categories = {}
        if not IPerson.providedBy(self.context):
            branches = self.context.branches
        else:
            url = self.request.getURL()
            if '+authoredbranches' in url:
                branches = self.context.authored_branches
            elif '+registeredbranches' in url:
                branches = self.context.registered_branches
            elif '+subscribedbranches' in url:
                branches = self.context.subscribed_branches
            else:
                branches = self.context.branches

        # Currently 500 branches is causing a timeout in the rendering of
        # the page template, and since we don't want it taking too long,
        # we are going to limit it here to 250 until we add batching.
        # This method is only called for the detailed listing pages,
        # which include more embedded queries, and hence take longer.
        # This is the reason for the different numbers above and here.
        # We don't want to make them configurable as this might show
        # intent that the solution will hang around when really it
        # is a temporary fix.
        #    -- Tim Penhey 2006-10-10
        for branch in shortlist(branches, 200, hardlimit=250):
            if categories.has_key(branch.lifecycle_status):
                category = categories[branch.lifecycle_status]
            else:
                category = {}
                category['status'] = branch.lifecycle_status
                category['branches'] = []
                categories[branch.lifecycle_status] = category
            category['branches'].append(branch)
        categories = categories.values()
        for category in categories:
            category['branches'].sort(key=operator.attrgetter('sort_key'))
        return sorted(categories, key=self.category_sortkey)

    @staticmethod
    def category_sortkey(category):
        return category['status'].sortkey


class PersonBranchesView(BranchTargetView):
    """View used for the tabular listing of branches related to a person.

    The context must provide IPerson.
    """

    def _branches(self):
        """All branches related to this target, sorted for display."""
        branches = set(self.context.branches)
        branches.update(self._team_branches_set)
        items = shortlist(branches, 1000, hardlimit=1500)
        return sorted(items, key=operator.attrgetter('sort_key'))

    @cachedproperty
    def _team_branches_set(self):
        """Return a set for efficient membership checks in branch_role."""
        teams = self.context.teams_participated_in
        branches = shortlist(
            getUtility(IBranchSet).getBranchesForOwners(teams),
            1000, hardlimit=1500)
        return set(branches)

    @cachedproperty
    def _authored_branch_set(self):
        """Set of branches authored by the person."""
        # must be cached because it is used by branch_role
        return set(self.context.authored_branches)

    @cachedproperty
    def _registered_branch_set(self):
        """Set of branches registered but not authored by the person."""
        # must be cached because it is used by branch_role
        return set(self.context.registered_branches)

    @cachedproperty
    def _subscribed_branch_set(self):
        """Set of branches this person is subscribed to."""
        # must be cached because it is used by branch_role
        return set(self.context.subscribed_branches)

    def branch_role(self, branch):
        """Primary role of this person for this branch.

        This explains why a branch appears on the person's page. The person may
        be 'Author', 'Registrant' or 'Subscriber'.

        :precondition: the branch must be part of the list provided by
            PersonBranchesView.branches.
        :return: dictionary of two items: 'title' and 'sortkey' describing the
            role of this person for this branch.
        """
        if branch in self._authored_branch_set:
            return {'title': 'Author', 'sortkey': 10}
        if branch in self._registered_branch_set:
            return {'title': 'Registrant', 'sortkey': 20}
        if branch in self._team_branches_set:
            return {'title': 'Team Branch', 'sortkey': 40}
        assert branch in self._subscribed_branch_set, (
            "Unable determine role of person %r for branch %r" % (
            self.context.name, branch.unique_name))
        return {'title': 'Subscriber', 'sortkey': 30}
        
    def getListingItems(self):
        """Return a list of decorated branches for easy TAL access."""
        return [BranchListingItem(branch,
                                  self.last_commit[branch],
                                  self.branch_bug_links.get(branch.id, None),
                                  self.branch_role(branch))
                for branch in self.visible_branches]
