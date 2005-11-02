# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

from datetime import datetime, timedelta
import pytz

from zope.component import getUtility

from canonical.launchpad.interfaces import IBranch, IBranchSet, ILaunchBag
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission, LaunchpadView)

__all__ = [
    'BranchAddView',
    'BranchContextMenu',
    'BranchEditView',
    'BranchPullListing',
    'BranchView',
    ]


class BranchContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = IBranch
    links = ['edit', 'lifecycle', 'subscription', 'administer']

    def edit(self):
        text = 'Edit Branch Details'
        return Link('+edit', text, icon='edit')

    def lifecycle(self):
        text = 'Set Branch Status'
        return Link('+lifecycle', text, icon='edit')

    def subscription(self):
        user = self.user
        if user is not None and has_branch_subscription(user, self.context):
            text = 'Unsubscribe'
        else:
            text = 'Subscribe'
        return Link('+subscribe', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')


def has_branch_subscription(person, branch):
    """Return whether the person has a subscription to the branch.

    XXX: Refactor this to a method on IBranch.
         DavidAllouche, 2005-09-26
    """
    assert person is not None
    for subscription in branch.subscriptions:
        if subscription.person.id == person.id:
            return True
    return False


class BranchView(LaunchpadView):

    __used_for__ = IBranch

    def initialize(self):
        self.notices = []
        # establish if a subscription form was posted
        newsub = self.request.form.get('subscribe', None)
        if newsub is not None and self.user and self.request.method == 'POST':
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                self.notices.append("You have subscribed to this branch.")
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                self.notices.append("You have unsubscribed from this branch.")

    def url(self):
        components = self.context.url.split('/')
        return '/&#x200B;'.join(components)

    @property
    def subscription(self):
        """BranchSubscription for the current user and this branch, or None."""
        if self.user is None:
            return None
        for subscription in self.context.subscriptions:
            if subscription.person.id == self.user.id:
                return subscription
        return None

    def count_revisions(self, days=30):
        """Number of revisions committed during the last N days."""
        timestamp = datetime.now(pytz.UTC) - timedelta(days=days)
        return self.context.revisions_since(timestamp).count()


class BranchEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class BranchAddView(SQLObjectAddView):
    """Add new branch."""

    _nextURL = None    

    def create(self, name, owner, author, product, url, title,
               lifecycle_status, summary, home_page):
        """Handle a request to create a new branch for this product."""        
        branch_set = getUtility(IBranchSet)
        branch = branch_set.new(
            name=name, owner=owner, author=author, product=product, url=url,
            title=title, lifecycle_status=lifecycle_status, summary=summary,
            home_page=home_page)
        self._nextURL = canonical_url(branch)

    def nextURL(self):
        assert self._nextURL
        return self._nextURL

        
class BranchPullListing(LaunchpadView):
    """A listing of all the branches in the system that are pending-pull."""

    def branch_line(self, branch):
        """Return the line in the listing for a single branch.
        
        XXX: The product name mangling should be hooked into Navigation by
             Steve Alexander when working on that.
        """
        if branch.product is None:
            productname = "+junk"
        else:
            productname = branch.product.name
        return "%s %s %s %s" % (branch.url, branch.author.name, productname,
                                branch.name)

    def branches_page(self, branches):
        """Return the full page for the supplied list of branches."""
        lines = [self.branch_line(branch)+ "\n" for branch in branches]
        return "".join(lines)

    def branches_to_pull(self):
        """What branches need to be pulled at this point?."""
        branch_set = getUtility(IBranchSet)
        return branch_set.get_supermirror_pull_queue()

    def render(self):
        """See LaunchpadView.render."""
        self.request.response.setHeader('Content-type', 'text/plain')
        branches = self.branches_to_pull()
        return self.branches_page(branches)
