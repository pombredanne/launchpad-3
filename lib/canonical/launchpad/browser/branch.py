# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

__all__ = [
    'BranchAddView',
    'BranchContextMenu',
    'BranchEditView',
    'BranchPullListing',
    'BranchView',
    ]

from datetime import datetime, timedelta
import pytz

from zope.component import getUtility

from canonical.launchpad.interfaces import IBranch, IBranchSet, ILaunchBag
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.addview import SQLObjectAddView

from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission, LaunchpadView)


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
        if user is not None and self.context.has_subscription(user):
            text = 'Unsubscribe'
        else:
            text = 'Subscribe'
        return Link('+subscribe', text, icon='edit')

    @enabled_with_permission('launchpad.Admin')
    def administer(self):
        text = 'Administer'
        return Link('+admin', text, icon='edit')


class BranchView(LaunchpadView):

    __used_for__ = IBranch

    def initialize(self):
        self.notices = []
        self._add_subscription_notice()

    def _add_subscription_notice(self):
        """Add the appropriate notice after posting the subscription form."""
        if self.user and self.request.method == 'POST':
            newsub = self.request.form.get('subscribe', None)
            if newsub == 'Subscribe':
                self.context.subscribe(self.user)
                self.notices.append("You have subscribed to this branch.")
            elif newsub == 'Unsubscribe':
                self.context.unsubscribe(self.user)
                self.notices.append("You have unsubscribed from this branch.")

    @property
    def user_is_subscribed(self):
        """Is the current user subscribed to this branch?"""
        if self.user is None:
            return False
        return self.context.has_subscription(self.user)

    def count_revisions(self, days=30):
        """Number of revisions committed during the last N days."""
        timestamp = datetime.now(pytz.UTC) - timedelta(days=days)
        return self.context.revisions_since(timestamp).count()

    def author_is_owner(self):
        """Is the branch author set and equal to the registrant?"""
        return self.context.author == self.context.owner


class BranchEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class BranchAddView(SQLObjectAddView):

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
        assert self._nextURL is not None, 'nextURL was called before create()'
        return self._nextURL

        
class BranchPullListing(LaunchpadView):
    """Listing of all the branches that the Supermirror should pull soon.

    The Supermirror periodically copies Bazaar branches from the internet. It
    gets the list of branches to pull, and associated data, by loading and
    parsing this page. This is only a transitional solution until the
    Supermirror can query Launchpad directly through a xmlrpc interface.
    """

    def get_line_for_branch(self, branch):
        """Format the information required to pull a single branch.

        :type branch: `IBranch`
        :rtype: unicode

        XXX: The product name mangling should be hooked into Navigation by
             Steve Alexander when working on that.
        """
        if branch.product is None:
            product_name = '+junk'
        else:
            product_name = branch.product.name
        return u'%s %s %s %s' % (branch.url, branch.owner.name, product_name,
                                 branch.name)

    def branches_page(self, branches):
        """Return the full page for the supplied list of branches."""
        lines = [self.get_line_for_branch(branch) for branch in branches]
        if not lines:
            return ''
        else:
            return '\n'.join(lines) + '\n'

    def get_branches_to_pull(self):
        """The branches that currently need to be pulled.

        :rtype: iterable of `IBranch`
        """
        branch_set = getUtility(IBranchSet)
        return branch_set.get_supermirror_pull_queue()

    def render(self):
        """Render a plaintext page with all branches that need pulling.

        :see: overrides `LaunchpadView.render`.
        """
        self.request.response.setHeader('Content-type', 'text/plain')
        branches = self.get_branches_to_pull()
        return self.branches_page(branches)
