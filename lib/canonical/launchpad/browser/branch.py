# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

__all__ = [
    'PersonBranchAddView',
    'ProductBranchAddView',
    'BranchContextMenu',
    'BranchEditView',
    'BranchReassignmentView',
    'BranchNavigation',
    'BranchInPersonView',
    'BranchInProductView',
    'BranchView',
    ]

import cgi
from datetime import datetime, timedelta
import pytz

from zope.event import notify
from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.launchpad.browser.branchref import BranchRef
from canonical.launchpad.browser.person import ObjectReassignmentView
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import (
    IBranch, IBranchSet, IBugSet)
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadView, Navigation, stepto, stepthrough, LaunchpadFormView,
    LaunchpadEditFormView, action, custom_widget)
from canonical.launchpad.webapp.uri import URI
from canonical.widgets import ContextWidget


def quote(text):
    return cgi.escape(text, quote=True)


class BranchNavigation(Navigation):

    usedfor = IBranch

    @stepthrough("+bug")
    def traverse_bug_branch(self, bugid):
        """Traverses to an IBugBranch."""
        bug = getUtility(IBugSet).get(bugid)

        for bug_branch in bug.bug_branches:
            if bug_branch.branch == self.context:
                return bug_branch

    @stepto(".bzr")
    def dotbzr(self):
        return BranchRef(self.context)


class BranchContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = IBranch
    facet = 'branches'
    links = ['edit', 'browse', 'reassign', 'subscription']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change branch details'
        return Link('+edit', text, icon='edit')

    def browse(self):
        text = 'Browse code'
        # Only enable the link if we've ever mirrored the branch.
        enabled = self.context.last_mirrored_id is not None
        url = config.launchpad.codebrowse_root + self.context.unique_name
        return Link(url, text, icon='info', enabled=enabled)

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change registrant'
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

    def mirror_of_ssh(self):
        """True if this a mirror branch with an sftp or bzr+ssh URL."""
        if not self.context.url:
            return False # not a mirror branch
        uri = URI(self.context.url)
        return uri.scheme in ('sftp', 'bzr+ssh')

    def show_mirror_failure(self):
        """True if mirror_of_ssh is false and branch mirroring failed."""
        if self.mirror_of_ssh():
            # SSH branches can't be mirrored, so a general failure message
            # is shown instead of the reported errors.
            return False
        else:
            return self.context.mirror_failures

    def user_can_upload(self):
        """Whether the user can upload to this branch."""
        return self.user.inTeam(self.context.owner)

    def upload_url(self):
        """The URL the logged in user can use to upload to this branch."""
        return 'sftp://%s@bazaar.launchpad.net/%s' % (
            self.user.name, self.context.unique_name)

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


class BranchNameValidationMixin:
    """Provide name validation logic used by several branch view classes."""

    def validate_branch_name(self, owner, product, branch_name):
        if product is None:
            product_name = None
        else:
            product_name = product.name

        branch = owner.getBranch(product_name, branch_name)

        # If the branch exists and isn't this branch, then we have a
        # name conflict.
        if branch is not None and branch != self.context:
            self.setFieldError('name',
                "Name already in use. You are the registrant of "
                "<a href=\"%s\">%s</a>,  the unique identifier of that "
                "branch is \"%s\". Change the name of that branch, or use "
                "a name different from \"%s\" for this branch."
                % (quote(canonical_url(branch)),
                   quote(branch.displayname),
                   quote(branch.unique_name),
                   quote(branch_name)))


class BranchEditFormView(LaunchpadEditFormView):
    """Base class for forms that edit a branch."""

    schema = IBranch
    field_names = None

    @action('Change Branch', name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)

    @property
    def next_url(self):
        return canonical_url(self.context)


class BranchEditView(BranchEditFormView, BranchNameValidationMixin):

    schema = IBranch
    field_names = ['product', 'url', 'name', 'title', 'summary',
                   'lifecycle_status', 'whiteboard', 'home_page', 'author']

    def setUpFields(self):
        LaunchpadFormView.setUpFields(self)
        # This is to prevent users from converting push/import
        # branches to pull branches.
        if self.context.url is None:
            self.form_fields = self.form_fields.omit('url')

    def validate(self, data):
        if 'product' in data and 'name' in data:
            self.validate_branch_name(self.context.owner,
                                      data['product'],
                                      data['name'])


class BranchAddView(LaunchpadFormView, BranchNameValidationMixin):

    schema = IBranch
    field_names = ['product', 'url', 'name', 'title', 'summary',
                   'lifecycle_status', 'whiteboard', 'home_page', 'author']

    branch = None

    @action('Add Branch', name='add')
    def add_action(self, action, data):
        """Handle a request to create a new branch for this product."""
        self.branch = getUtility(IBranchSet).new(
            name=data['name'],
            owner=self.user,
            author=self.getAuthor(data),
            product=self.getProduct(data),
            url=data['url'],
            title=data['title'],
            summary=data['summary'],
            lifecycle_status=data['lifecycle_status'],
            home_page=data['home_page'],
            whiteboard=data['whiteboard'])
        notify(SQLObjectCreatedEvent(self.branch))

    def getAuthor(self, data):
        """A method that is overridden in the derived classes."""
        return data['author']

    def getProduct(self, data):
        """A method that is overridden in the derived classes."""
        return data['product']

    @property
    def next_url(self):
        assert self.branch is not None, 'next_url called when branch is None'
        return canonical_url(self.branch)

    def validate(self, data):
        if 'product' in data and 'name' in data:
            self.validate_branch_name(self.user,
                                      data['product'],
                                      data['name'])
    def script_hook(self):
        return '''<script type="text/javascript">

        function populate_name() {
          populate_branch_name_from_url('%(name)s', '%(url)s')
        }
        var url_field = document.getElementById('%(url)s');
        // Since it is possible that the form could be submitted without
        // the onblur getting called, and onblur can be called without
        // onchange being fired, set them both, and handle it in the function.
        url_field.onchange = populate_name;
        url_field.onblur = populate_name;
        </script>''' % { 'name' : self.widgets['name'].name,
                         'url' : self.widgets['url'].name } 


class PersonBranchAddView(BranchAddView):
    """See BranchAddView."""

    @property
    def field_names(self):
        fields = list(BranchAddView.field_names)
        fields.remove('author')
        return fields

    def getAuthor(self, data):
        return self.context

class ProductBranchAddView(BranchAddView):
    """See BranchAddView."""

    initial_focus_widget = 'url'
    
    @property
    def field_names(self):
        fields = list(BranchAddView.field_names)
        fields.remove('product')
        return fields

    def getProduct(self, data):
        return self.context

    def validate(self, data):
        if 'name' in data:
            self.validate_branch_name(self.user, self.context, data['name'])

    @property
    def initial_values(self):
        return {'author': self.user}


class BranchReassignmentView(ObjectReassignmentView):
    """Reassign branch to a new owner."""

    # XXX: this view should have a "name" field to allow the user to resolve a
    # name conflict without going to another page, but this is hard to do
    # because ObjectReassignmentView uses a custom form.
    # -- David Allouche 2006-08-16

    @property
    def nextUrl(self):
        return canonical_url(self.context)

    def isValidOwner(self, new_owner):
        if self.context.product is None:
            product_name = None
        else:
            product_name = self.context.product.name
        branch_name = self.context.name
        branch = new_owner.getBranch(product_name, branch_name)
        if branch is None:
            # No matching branch, reassignation is possible.
            return True
        elif branch == self.context:
            # That should only happen if the owner has not changed.
            # In any case, a branch does not conflict with itself.
            return True
        else:
            # Here we have a name conflict.
            self.errormessage = (
                "Branch name conflict."
                " There is already a branch registered by %s in %s"
                " with the name %s."
                " You can edit this branch details to change its name,"
                " and try changing its registrant again."
                % (quote(new_owner.browsername),
                   quote(branch.product.displayname),
                   branch.name))
            return False
