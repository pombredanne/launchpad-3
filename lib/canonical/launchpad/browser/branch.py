# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

__all__ = [
    'BranchSOP',
    'PersonBranchAddView',
    'ProductBranchAddView',
    'BranchContextMenu',
    'BranchEditView',
    'BranchReassignmentView',
    'BranchNavigation',
    'BranchInPersonView',
    'BranchInProductView',
    'BranchView',
    'BranchSubscriptionsView',
    ]

import cgi
from datetime import datetime, timedelta
import pytz

from zope.event import notify
from zope.component import getUtility

from canonical.config import config

from canonical.lp import decorates

from canonical.launchpad.browser.branchref import BranchRef
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.browser.person import ObjectReassignmentView
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.helpers import truncate_text
from canonical.launchpad.interfaces import (
    BranchCreationForbidden, BranchType, BranchVisibilityRule, IBranch,
    IBranchSet, IBranchSubscription, IBugSet,
    ICodeImportSet, ILaunchpadCelebrities, IPersonSet)
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadView, Navigation, stepto, stepthrough, LaunchpadFormView,
    LaunchpadEditFormView, action)
from canonical.launchpad.webapp.uri import URI


def quote(text):
    return cgi.escape(text, quote=True)


class BranchSOP(StructuralObjectPresentation):
    """Provides the structural heading for `IBranch`."""

    def getMainHeading(self):
        """See `IStructuralHeaderPresentation`."""
        return self.context.owner.browsername


class BranchNavigation(Navigation):

    usedfor = IBranch

    @stepthrough("+bug")
    def traverse_bug_branch(self, bugid):
        """Traverses to an `IBugBranch`."""
        bug = getUtility(IBugSet).get(bugid)

        for bug_branch in bug.bug_branches:
            if bug_branch.branch == self.context:
                return bug_branch

    @stepto(".bzr")
    def dotbzr(self):
        return BranchRef(self.context)

    @stepthrough("+subscription")
    def traverse_subscription(self, name):
        """Traverses to an `IBranchSubcription`."""
        person = getUtility(IPersonSet).getByName(name)

        if person is not None:
            return self.context.getSubscription(person)

    @stepto("+code-import")
    def traverse_code_import(self):
        """Traverses to an `ICodeImport`."""
        return getUtility(ICodeImportSet).getByBranch(self.context)


class BranchContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = IBranch
    facet = 'branches'
    links = ['edit', 'browse', 'reassign', 'subscription', 'addsubscriber',
             'associations']

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

    @enabled_with_permission('launchpad.AnyPerson')
    def subscription(self):
        if self.context.hasSubscription(self.user):
            url = '+edit-subscription'
            text = 'Edit subscription'
            icon = 'edit'
        else:
            url = '+subscribe'
            text = 'Subscribe'
            icon = 'add'
        return Link(url, text, icon=icon)

    @enabled_with_permission('launchpad.AnyPerson')
    def addsubscriber(self):
        text = 'Subscribe someone else'
        return Link('+addsubscriber', text, icon='add')

    def associations(self):
        text = 'View branch associations'
        return Link('+associations', text)


class BranchView(LaunchpadView):

    __used_for__ = IBranch

    MAXIMUM_STATUS_MESSAGE_LENGTH = 128

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
        return self.context.hasSubscription(self.user)

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
        # XXX: DavidAllouche 2005-12-02 bug=5313:
        # That should go away when bug #5313 is fixed.
        linkdata = BranchContextMenu(self.context).edit()
        return '%s/%s' % (canonical_url(self.context), linkdata.target)

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

    def is_hosted_branch(self):
        """Whether this is a user-provided hosted branch."""
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        return self.context.url is None and self.context.owner != vcs_imports

    def mirror_status_message(self):
        """A message from a bad scan or pull, truncated for display."""
        message = self.context.mirror_status_message
        if len(message) <= self.MAXIMUM_STATUS_MESSAGE_LENGTH:
            return message
        return truncate_text(
            message, self.MAXIMUM_STATUS_MESSAGE_LENGTH) + ' ...'


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
    field_names = ['product', 'private', 'url', 'name', 'title', 'summary',
                   'lifecycle_status', 'whiteboard', 'home_page', 'author']

    def setUpFields(self):
        LaunchpadFormView.setUpFields(self)
        # This is to prevent users from converting push/import
        # branches to pull branches.
        branch = self.context
        if branch.url is None:
            self.form_fields = self.form_fields.omit('url')

        # Disable privacy if the owner of the branch is not allowed to change
        # the branch from private to public, or is not allowed to have private
        # branches for the project.
        product = branch.product
        # No privacy set for junk branches
        if product is None:
            hide_private_field = True
        else:
            # If there is an explicit rule for the team, then that overrides
            # any rule specified for other teams that the owner is a member
            # of.
            rule = product.getBranchVisibilityRuleForBranch(branch)
            if rule == BranchVisibilityRule.PRIVATE_ONLY:
                # If the branch is already private, then the user cannot
                # make the branch public.  However if the branch is for
                # some reason public, then the user is allowed to make
                # it private.
                hide_private_field = branch.private
            elif rule == BranchVisibilityRule.PRIVATE:
                hide_private_field = False
            else:
                hide_private_field = True

        if hide_private_field:
            self.form_fields = self.form_fields.omit('private')

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
        try:
            # XXX thumper 2007-06-27 spec=branch-creation-refactoring:
            # The branch_type needs to be passed
            # in as part of the view data, see spec
            self.branch = getUtility(IBranchSet).new(
                branch_type=BranchType.MIRRORED,
                name=data['name'],
                creator=self.user,
                owner=self.user,
                author=self.getAuthor(data),
                product=self.getProduct(data),
                url=data['url'],
                title=data['title'],
                summary=data['summary'],
                lifecycle_status=data['lifecycle_status'],
                home_page=data['home_page'],
                whiteboard=data['whiteboard'])
        except BranchCreationForbidden:
            self.setForbiddenError(self.getProduct(data))
        else:
            notify(SQLObjectCreatedEvent(self.branch))
            self.next_url = canonical_url(self.branch)

    def setForbiddenError(self, product):
        """Method provided so the error handling can be overridden."""
        assert product is not None, (
            "BranchCreationForbidden should never be raised for "
            "junk branches.")
        self.setFieldError(
            'product',
            "You are not allowed to create branches in %s."
            % (quote(product.displayname)))

    def getAuthor(self, data):
        """A method that is overridden in the derived classes."""
        return data['author']

    def getProduct(self, data):
        """A method that is overridden in the derived classes."""
        return data['product']

    def validate(self, data):
        if 'product' in data and 'name' in data:
            self.validate_branch_name(
                self.user, data['product'], data['name'])

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
            </script>''' % {'name': self.widgets['name'].name,
                            'url': self.widgets['url'].name}


class PersonBranchAddView(BranchAddView):
    """See `BranchAddView`."""

    @property
    def field_names(self):
        fields = list(BranchAddView.field_names)
        fields.remove('author')
        return fields

    def getAuthor(self, data):
        return self.context


class ProductBranchAddView(BranchAddView):
    """See `BranchAddView`."""

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

    def setForbiddenError(self, product):
        """There is no product widget, so set a form wide error."""
        assert product is not None, (
            "BranchCreationForbidden should never be raised for "
            "junk branches.")
        self.addError(
            "You are not allowed to create branches in %s."
            % (quote(product.displayname)))


class BranchReassignmentView(ObjectReassignmentView):
    """Reassign branch to a new owner."""

    # XXX: David Allouche 2006-08-16:
    # This view should have a "name" field to allow the user to resolve a
    # name conflict without going to another page, but this is hard to do
    # because ObjectReassignmentView uses a custom form.

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


class DecoratedSubscription:
    """Adds the editable attribute to a `BranchSubscription`."""
    decorates(IBranchSubscription, 'subscription')

    def __init__(self, subscription, editable):
        self.subscription = subscription
        self.editable = editable


class BranchSubscriptionsView(LaunchpadView):
    """The view for the branch subscriptions portlet.

    The view is used to provide a decorated list of branch subscriptions
    in order to provide links to be able to edit the subscriptions
    based on whether or not the user is able to edit the subscription.
    """

    def isEditable(self, subscription):
        """A subscription is editable by members of the subscribed team.

        Launchpad Admins are special, and can edit anyone's subscription.
        """
        # We don't want to say editable if the logged in user
        # is the same as the person of the subscription.
        if self.user is None or self.user == subscription.person:
            return False
        admins = getUtility(ILaunchpadCelebrities).admin
        return (self.user.inTeam(subscription.person) or
                self.user.inTeam(admins))

    def subscriptions(self):
        """Return a decorated list of branch subscriptions."""
        sorted_subscriptions = sorted(
            self.context.subscriptions,
            key=lambda subscription: subscription.person.browsername)
        return [DecoratedSubscription(
                    subscription, self.isEditable(subscription))
                for subscription in sorted_subscriptions]
