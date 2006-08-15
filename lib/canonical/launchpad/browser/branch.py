# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

__all__ = [
    'BranchAddView',
    'ProductBranchAddView',
    'BranchContextMenu',
    'BranchEditView',
    'BranchLifecycleView',
    'BranchReassignmentView',
    'BranchNavigation',
    'BranchInPersonView',
    'BranchInProductView',
    'BranchUrlWidget',
    'BranchView',
    ]

from datetime import datetime, timedelta
import pytz

from zope.event import notify
from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.browser.person import ObjectReassignmentView
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import (
    IBranch, IBranchSet, IBugSet)
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadView, Navigation, stepthrough, LaunchpadFormView,
    LaunchpadEditFormView, action, custom_widget)
from canonical.widgets import ContextWidget
from canonical.widgets.textwidgets import StrippedTextWidget


class BranchNavigation(Navigation):

    usedfor = IBranch

    @stepthrough("+bug")
    def traverse_bug_branch(self, bugid):
        """Traverses to an IBugBranch."""
        bug = getUtility(IBugSet).get(bugid)

        for bug_branch in bug.bug_branches:
            if bug_branch.branch == self.context:
                return bug_branch


class BranchContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = IBranch
    facet = 'branches'
    links = ['edit', 'lifecycle', 'reassign', 'subscription']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Edit Branch Details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def lifecycle(self):
        text = 'Set Branch Status'
        return Link('+lifecycle', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change Registrant'
        return Link('+reassign', text, icon='edit')

    def subscription(self):
        user = self.user
        if user is not None and self.context.has_subscription(user):
            text = 'Unsubscribe'
        else:
            text = 'Subscribe'
        return Link('+subscribe', text, icon='edit')


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

    def user_is_subscribed(self):
        """Is the current user subscribed to this branch?"""
        if self.user is None:
            return False
        return self.context.has_subscription(self.user)

    @cachedproperty
    def revision_count(self):
        # Avoid hitting the database multiple times, which is expensive
        # because it issues a COUNT
        return self.context.revision_count()

    def recent_revision_count(self, days=30):
        """Number of revisions committed during the last N days."""
        timestamp = datetime.now(pytz.UTC) - timedelta(days=days)
        return self.context.revisions_since(timestamp).count()

    def author_is_owner(self):
        """Is the branch author set and equal to the registrant?"""
        return self.context.author == self.context.owner

    def supermirror_url(self):
        """Public URL of the branch on the Supermirror."""
        return config.launchpad.supermirror_root + self.context.unique_name

    def edit_link_url(self):
        """Target URL of the Edit link used in the actions portlet."""
        # XXX: that should go away when bug #5313 is fixed.
        #  -- DavidAllouche 2005-12-02
        linkdata = BranchContextMenu(self.context).edit()
        return '%s/%s' % (canonical_url(self.context), linkdata.target)

    def url(self):
        """URL where the branch can be checked out.

        This is the URL set in the database, or the Supermirror URL.
        """
        if self.context.url:
            return self.context.url
        else:
            return self.supermirror_url()

    def missing_title_or_summary_text(self):
        if self.context.title:
            if self.context.summary:
                return None
            else:
                return '(this branch has no summary)'
        else:
            if self.context.summary:
                return '(this branch has no title)'
            else:
                return '(this branch has neither title nor summary)'


class BranchInPersonView(BranchView):

    show_person_link = False

    @property
    def show_product_link(self):
        return self.context.product is not None


class BranchInProductView(BranchView):

    show_person_link = True
    show_product_link = False


class BranchUrlWidget(StrippedTextWidget):
    """A widget to capture the URL of a remote branch.

    Wider than a normal TextLine widget and ignores trailing slashes.
    """
    displayWidth = 44
    cssClass = 'urlTextType'

    def _toFieldValue(self, input):
        if input == self._missing:
            return self.context.missing_value
        else:
            value = StrippedTextWidget._toFieldValue(self, input)
            return value.rstrip('/')


class BranchHomePageWidget(StrippedTextWidget):
    """A widget to capture a web page URL, wider than a normal TextLine."""
    displayWidth = 44
    cssClass = 'urlTextType'


class BranchEditView(LaunchpadEditFormView):

    schema = IBranch
    field_names = ['product', 'url', 'name', 'title', 'summary', 'whiteboard',
                   'home_page', 'author']

    custom_widget('url', BranchUrlWidget)
    custom_widget('home_page', BranchHomePageWidget)

    def setUpFields(self):
        LaunchpadFormView.setUpFields(self)
        # This is to prevent users from converting push/import
        # branches to pull branches.
        if self.context.url is None:
            self.form_fields = self.form_fields.omit('url')

    @action('Change Branch', name='change')
    def change_action(self, action, data):
        self.update_context_from_data(data)

    @property
    def next_url(self):
        return canonical_url(self.context)


class BranchLifecycleView(BranchEditView):

    label = "Set branch status"
    field_names = ['lifecycle_status', 'whiteboard']


class BranchAdminView(BranchEditView):

    label = "Branch administration"
    field_names = ['owner', 'product', 'name', 'whiteboard']


class BranchAddView(LaunchpadFormView):

    schema = IBranch
    field_names = ['product', 'url', 'name', 'title', 'summary',
                   'lifecycle_status', 'whiteboard', 'home_page', 'author']

    custom_widget('url', BranchUrlWidget)
    custom_widget('home_page', BranchHomePageWidget)
    custom_widget('author', ContextWidget)

    branch = None

    @action('Add Branch', name='add')
    def add_action(self, action, data):
        """Handle a request to create a new branch for this product."""
        self.branch = getUtility(IBranchSet).new(
            name=data['name'],
            owner=self.user,
            author=data['author'],
            product=data['product'],
            url=data['url'],
            title=data['title'],
            summary=data['summary'],
            lifecycle_status=data['lifecycle_status'],
            home_page=data['home_page'],
            whiteboard=data['whiteboard'])
        notify(SQLObjectCreatedEvent(self.branch))

    @property
    def next_url(self):
        assert self.branch is not None, 'next_url called when branch is None'
        return canonical_url(self.branch)


class ProductBranchAddView(BranchAddView):
    custom_widget('author', None)
    custom_widget('product', ContextWidget)


class BranchReassignmentView(ObjectReassignmentView):
    """Reassign branch to a new owner."""

    # FIXME: will OOPS when trying to reassign a branch to a person which
    # already has a branch with the same name and product.
    # -- David Allouche 2006-08-10

    @property
    def nextUrl(self):
        return canonical_url(self.context)
