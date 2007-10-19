# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

__all__ = [
    'BranchSOP',
    'PersonBranchAddView',
    'ProductBranchAddView',
    'BranchBadges',
    'BranchContextMenu',
    'BranchDeletionView',
    'BranchEditView',
    'BranchReassignmentView',
    'BranchMirrorStatusView',
    'BranchNavigation',
    'BranchInPersonView',
    'BranchInProductView',
    'BranchView',
    'BranchSubscriptionsView',
    'RegisterBranchMergeProposalView',
    ]

import cgi
from datetime import datetime, timedelta
import pytz

from zope.event import notify
from zope.component import getUtility
from zope.interface import Interface

from canonical.cachedproperty import cachedproperty
from canonical.config import config

from canonical.lp import decorates
from canonical.launchpad.browser.branchref import BranchRef
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.browser.objectreassignment import (
    ObjectReassignmentView)
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.helpers import truncate_text
from canonical.launchpad.interfaces import (
    BranchCreationForbidden, BranchType, BranchVisibilityRule, IBranch,
    IBranchMergeProposal, InvalidBranchMergeProposal,
    IBranchSet, IBranchSubscription, IBugSet,
    ICodeImportSet, ILaunchpadCelebrities, IPersonSet, MIRROR_TIME_INCREMENT,
    UICreatableBranchType)
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadView, Navigation, stepto, stepthrough, LaunchpadFormView,
    LaunchpadEditFormView, action, custom_widget)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.badge import Badge, HasBadgeBase
from canonical.launchpad.webapp.uri import URI

from canonical.widgets import SinglePopupWidget


def quote(text):
    return cgi.escape(text, quote=True)


class BranchSOP(StructuralObjectPresentation):
    """Provides the structural heading for `IBranch`."""

    def isPrivate(self):
        return self.context.private

    def getMainHeading(self):
        """See `IStructuralHeaderPresentation`."""
        return self.context.owner.browsername


class BranchBadges(HasBadgeBase):
    badges = "private", "bug", "blueprint", "warning"

    def __init__(self, branch):
        self.branch = branch

    def isPrivateBadgeVisible(self):
        """Show a private badge if the branch is private."""
        return self.branch.private

    def isBugBadgeVisible(self):
        """Show a bug badge if the branch is linked to bugs."""
        # Only show the badge if at least one bug is visible by the user.
        for bug in self.branch.related_bugs:
            # Stop on the first visible one.
            if check_permission('launchpad.View', bug):
                return True
        return False

    def isBlueprintBadgeVisible(self):
        """Show a blueprint badge if the branch is linked to blueprints."""
        # When specs get privacy, this will need to be adjusted.
        return self.branch.spec_links.count() > 0

    def isWarningBadgeVisible(self):
        """Show a warning badge if there are mirror failures."""
        return self.branch.mirror_failures > 0

    def getBadge(self, badge_name):
        """See `IHasBadges`."""
        if badge_name == "warning":
            return Badge('/@@/warning', '/@@/warning-large', '',
                         'Branch has errors')
        else:
            return HasBadgeBase.getBadge(self, badge_name)


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

    @stepthrough("+merge")
    def traverse_merge_proposal(self, id):
        """Traverse to an `IBranchMergeProposal`."""
        try:
            id = int(id)
        except ValueError:
            # Not a number.
            return None
        for proposal in self.context.landing_targets:
            if proposal.id == id:
                return proposal

    @stepto("+code-import")
    def traverse_code_import(self):
        """Traverses to an `ICodeImport`."""
        return getUtility(ICodeImportSet).getByBranch(self.context)


class BranchContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = IBranch
    facet = 'branches'
    links = ['edit', 'delete_branch', 'browse_code', 'browse_revisions',
             'reassign', 'subscription', 'addsubscriber', 'associations',
             'registermerge', 'landingcandidates', 'linkbug']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change branch details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def delete_branch(self):
        text = 'Delete branch'
        enabled = self.context.canBeDeleted()
        return Link('+delete', text, enabled=enabled)

    def browse_code(self):
        """Return a link to the branch's file listing on codebrowse."""
        text = 'Browse code'
        enabled = self.context.code_is_browseable
        url = (config.codehosting.codebrowse_root
               + self.context.unique_name
               + '/files')
        return Link(url, text, icon='info', enabled=enabled)

    def browse_revisions(self):
        """Return a link to the branch's revisions on codebrowse."""
        text = 'Browse revisions'
        enabled = self.context.code_is_browseable
        url = (config.codehosting.codebrowse_root
               + self.context.unique_name
               + '/changes')
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

    @enabled_with_permission('launchpad.AnyPerson')
    def registermerge(self):
        text = 'Register merge proposal'
        return Link('+register-merge', text, icon='edit')

    def landingcandidates(self):
        text = 'View landing candidates'
        enabled = self.context.landing_candidates.count() > 0
        return Link('+landing-candidates', text, icon='edit', enabled=enabled)

    def linkbug(self):
        text = 'Link to bug report'
        return Link('+linkbug', text, icon='edit')


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
        return self.context.hasSubscription(self.user)

    def recent_revision_count(self, days=30):
        """Number of revisions committed during the last N days."""
        timestamp = datetime.now(pytz.UTC) - timedelta(days=days)
        return self.context.revisions_since(timestamp).count()

    def author_is_owner(self):
        """Is the branch author set and equal to the registrant?"""
        return self.context.author == self.context.owner

    @property
    def codebrowse_url(self):
        """Return the link to codebrowse for this branch."""
        return config.codehosting.codebrowse_root + self.context.unique_name

    def bzr_download_url(self):
        """Return the generic URL for downloading the branch."""
        if self.user_can_download():
            return self.context.getBzrDownloadURL()
        else:
            return None

    def bzr_user_download_url(self):
        """Return the specific URL for the user to download the branch."""
        if self.user_can_download():
            return self.context.getBzrDownloadURL(self.user)
        else:
            return None

    def bzr_upload_url(self):
        """Return the generic URL for uploading the branch."""
        if self.user_can_upload():
            return self.context.getBzrUploadURL()
        else:
            return None

    def bzr_user_upload_url(self):
        """Return the specific URL for the user to upload to the branch."""
        if self.user_can_upload():
            return self.context.getBzrUploadURL(self.user)
        else:
            return None

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

    def user_can_upload(self):
        """Whether the user can upload to this branch."""
        return (self.user is not None and
                self.user.inTeam(self.context.owner) and
                self.context.branch_type == BranchType.HOSTED)

    def user_can_download(self):
        """Whether the user can download this branch."""
        return (self.context.branch_type != BranchType.REMOTE and
                self.context.revision_count > 0)

    def is_hosted_branch(self):
        """Whether this is a user-provided hosted branch."""
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        return self.context.url is None and self.context.owner != vcs_imports

    @cachedproperty
    def landing_targets(self):
        """Return a decorated filtered list of landing targets."""
        targets = []
        targets_added = set()
        for proposal in self.context.landing_targets:
            # Only show the must recent proposal for any given target.
            target_id = proposal.target_branch.id
            if target_id in targets_added:
                continue
            targets.append(DecoratedMergeProposal(proposal))
            targets_added.add(target_id)
        return targets

    @cachedproperty
    def latest_landing_candidates(self):
        """Return a decorated filtered list of landing candidates."""
        # Only show the most recent 5 landing_candidates
        candidates = self.context.landing_candidates[:5]
        return [DecoratedMergeProposal(proposal) for proposal in candidates]

    @cachedproperty
    def landing_candidates(self):
        """Return a decorated list of landing candidates."""
        candidates = self.context.landing_candidates
        return [DecoratedMergeProposal(proposal) for proposal in candidates]


class DecoratedMergeProposal:
    """Provide some additional functionality to a normal branch merge proposal.
    """
    decorates(IBranchMergeProposal)

    def __init__(self, context):
        self.context = context

    def show_registrant(self):
        """Show the registrant if it was not the branch owner."""
        return self.context.registrant != self.source_branch.owner

    @cachedproperty
    def landing_targets(self):
        """Return a decorated filtered list of landing targets."""
        targets = []
        targets_added = set()
        for proposal in self.context.landing_targets:
            # Only show the must recent proposal for any given target.
            target_id = proposal.target_branch.id
            if target_id in targets_added:
                continue
            targets.append(DecoratedMergeProposal(proposal))
            targets_added.add(target_id)
        return targets

    @cachedproperty
    def latest_landing_candidates(self):
        """Return a decorated filtered list of landing candidates."""
        # Only show the most recent 5 landing_candidates
        candidates = self.context.landing_candidates[:5]
        return [DecoratedMergeProposal(proposal) for proposal in candidates]

    @cachedproperty
    def landing_candidates(self):
        """Return a decorated list of landing candidates."""
        candidates = self.context.landing_candidates
        return [DecoratedMergeProposal(proposal) for proposal in candidates]


class DecoratedMergeProposal:
    """Provide some additional functionality to a normal branch merge proposal.
    """
    decorates(IBranchMergeProposal)

    def __init__(self, context):
        self.context = context

    def show_registrant(self):
        """Show the registrant if it was not the branch owner."""
        return self.context.registrant != self.source_branch.owner


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


class BranchMirrorStatusView(LaunchpadFormView):
    """This view displays the mirror status of a branch.

    This includes the next mirror time and any failures that may have
    occurred.
    """

    MAXIMUM_STATUS_MESSAGE_LENGTH = 128

    schema = Interface

    field_names = []

    def in_mirror_queue(self):
        """Is it likely that the branch is being mirrored in the next run of
        the puller?
        """
        return self.context.mirror_request_time < datetime.now(pytz.UTC)

    def mirror_disabled(self):
        """Has mirroring this branch been disabled?"""
        return self.context.mirror_request_time is None

    def mirror_failed_once(self):
        """Has there been exactly one failed attempt to mirror this branch?"""
        return self.context.mirror_failures == 1

    def mirror_status_message(self):
        """A message from a bad scan or pull, truncated for display."""
        message = self.context.mirror_status_message
        if len(message) <= self.MAXIMUM_STATUS_MESSAGE_LENGTH:
            return message
        return truncate_text(
            message, self.MAXIMUM_STATUS_MESSAGE_LENGTH) + ' ...'

    def show_mirror_failure(self):
        """True if mirror_of_ssh is false and branch mirroring failed."""
        if URI(self.context.url).scheme in ('sftp', 'bzr+ssh'):
            # SSH branches can't be mirrored, so a general failure message
            # is shown instead of the reported errors.
            return False
        else:
            return self.context.mirror_failures

    @property
    def action_url(self):
        return "%s/+mirror-failures" % canonical_url(self.context)

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action('Try again', name='try-again')
    def retry(self, action, data):
        self.context.requestMirror()


class BranchDeletionView(LaunchpadFormView):
    """Used to delete a branch."""

    schema = IBranch
    field_names = []

    @action('Delete Branch', name='delete_branch')
    def delete_branch_action(self, action, data):
        branch = self.context
        if self.context.canBeDeleted():
            # Since the user is going to delete the branch, we need to have
            # somewhere valid to send them next.  Since most of the time it
            # will be the owner of the branch deleting it, we should send
            # them to the code listing for the owner.
            self.next_url = canonical_url(branch.owner)
            message = "Branch %s deleted." % branch.unique_name
            getUtility(IBranchSet).delete(branch)
            self.request.response.addNotification(message)
        else:
            self.request.response.addNotification(
                "This branch cannot be deleted.")
            self.next_url = canonical_url(branch)


class BranchEditView(BranchEditFormView, BranchNameValidationMixin):

    schema = IBranch
    field_names = ['product', 'private', 'url', 'name', 'title', 'summary',
                   'lifecycle_status', 'whiteboard', 'home_page', 'author']

    def setUpFields(self):
        LaunchpadFormView.setUpFields(self)
        # This is to prevent users from converting push/import
        # branches to pull branches.
        branch = self.context
        if branch.branch_type in (BranchType.HOSTED, BranchType.IMPORTED):
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
        # Check that we're not moving a team branch to the +junk
        # pseudo project.
        if ('product' in data and data['product'] is None
            and self.context.owner.isTeam()):
            self.setFieldError(
                'product',
                "Team-owned branches must be associated with a project.")
        if 'product' in data and 'name' in data:
            self.validate_branch_name(self.context.owner,
                                      data['product'],
                                      data['name'])

        # If the branch is a MIRRORED branch, then the url
        # must be supplied, and if HOSTED the url must *not*
        # be supplied.
        url = data.get('url')
        if self.context.branch_type == BranchType.MIRRORED:
            if url is None:
                # If the url is not set due to url validation errors,
                # there will be an error set for it.
                error = self.getWidgetError('url')
                if not error:
                    self.setFieldError(
                        'url',
                        'Branch URLs are required for Mirrored branches.')
        else:
            # We don't care about whether the URL is set for REMOTE branches,
            # and the URL field is not shown for IMPORT or HOSTED branches.
            pass


class BranchAddView(LaunchpadFormView, BranchNameValidationMixin):

    schema = IBranch
    field_names = ['branch_type', 'product', 'url', 'name', 'title', 'summary',
                   'lifecycle_status', 'whiteboard', 'home_page', 'author']

    branch = None

    @property
    def initial_values(self):
        return {'branch_type': UICreatableBranchType.MIRRORED}

    @action('Add Branch', name='add')
    def add_action(self, action, data):
        """Handle a request to create a new branch for this product."""
        try:
            ui_branch_type = data['branch_type']
            self.branch = getUtility(IBranchSet).new(
                branch_type=BranchType.items[ui_branch_type.name],
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
            if self.branch.branch_type == BranchType.MIRRORED:
                self.branch.requestMirror()
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

    def hasProduct(self, data):
        """Is the product defined in the data dict."""
        return 'product' in data

    def getProduct(self, data):
        """A method that is overridden in the derived classes."""
        return data.get('product')

    def validate(self, data):
        if self.hasProduct(data) and 'name' in data:
            self.validate_branch_name(
                self.user, self.getProduct(data), data['name'])

        branch_type = data.get('branch_type')
        # If branch_type failed to validate, then the rest of the method
        # doesn't make any sense.
        if branch_type is None:
            return

        # If the branch is a MIRRORED branch, then the url
        # must be supplied, and if HOSTED the url must *not*
        # be supplied.
        url = data.get('url')
        if branch_type == UICreatableBranchType.MIRRORED:
            if url is None:
                # If the url is not set due to url validation errors,
                # there will be an error set for it.
                error = self.getWidgetError('url')
                if not error:
                    self.setFieldError(
                        'url',
                        'Branch URLs are required for Mirrored branches.')
        elif branch_type == UICreatableBranchType.HOSTED:
            if url is not None:
                self.setFieldError(
                    'url',
                    'Branch URLs cannot be set for Hosted branches.')
        elif branch_type == UICreatableBranchType.REMOTE:
            # A remote location can, but doesn't have to be set.
            pass
        else:
            raise AssertionError('Unknown branch type')

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

    @property
    def field_names(self):
        fields = list(BranchAddView.field_names)
        fields.remove('product')
        return fields

    def hasProduct(self, data):
        return True

    def getProduct(self, data):
        return self.context

    @property
    def initial_values(self):
        return {'author': self.user,
                'branch_type': UICreatableBranchType.MIRRORED}

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
            if new_owner.isTeam():
                self.errormessage = (
                    "You cannot assign a +junk branch to a team. Create a "
                    "project first.")
                return False
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
            # XXX 2007-08-07 MichaelHudson, branch.product can be None in the
            # lines above.  See bug 133126.
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


class RegisterBranchMergeProposalView(LaunchpadFormView):
    """The view to register new branch merge proposals."""
    schema = IBranchMergeProposal
    for_input=True

    field_names = ['target_branch', 'dependent_branch', 'whiteboard']

    custom_widget('target_branch', SinglePopupWidget, displayWidth=35)
    custom_widget('dependent_branch', SinglePopupWidget, displayWidth=35)

    @action('Register', name='register')
    def register_action(self, action, data):
        """Register the new branch merge proposal."""

        registrant = self.user
        source_branch = self.context
        target_branch = data['target_branch']
        dependent_branch = data['dependent_branch']
        whiteboard = data['whiteboard']

        # If the dependent_branch is set explicitly the same as the
        # target_branch, it is the same as if it was not set at all.
        if dependent_branch == target_branch:
            dependent_branch = None

        try:
            source_branch.addLandingTarget(
                registrant=registrant, target_branch=target_branch,
                dependent_branch=dependent_branch, whiteboard=whiteboard)
        except InvalidBranchMergeProposal, error:
            self.addError(str(error))
        else:
            self.next_url = canonical_url(source_branch)

    def validate(self, data):
        source_branch = self.context
        target_branch = data.get('target_branch')
        dependent_branch = data.get('dependent_branch')

        # Make sure that the target branch is different from the context.
        if target_branch is None:
            # Skip the following tests.
            # The existance of the target_branch is handled by the form
            # machinery.
            pass
        elif source_branch == target_branch:
            self.setFieldError(
                'target_branch',
                "The target branch cannot be the same as the source branch.")
        else:
            # Make sure that the target_branch is in the same project.
            if target_branch.product != source_branch.product:
                self.setFieldError(
                    'target_branch',
                    "The target branch must belong to the same project "
                    "as the source branch.")

        if dependent_branch is None:
            # Skip the following tests.
            pass
        elif dependent_branch == source_branch:
            self.setFieldError(
                'dependent_branch',
                "The dependent branch cannot be the same as the source branch.")
        else:
            # Make sure that the dependent_branch is in the project.
            if dependent_branch.product != source_branch.product:
                self.setFieldError(
                    'dependent_branch',
                    "The dependent branch must belong to the same project "
                    "as the source branch.")
