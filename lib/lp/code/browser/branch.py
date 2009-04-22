# Copyright 2004-2009 Canonical Ltd.  All rights reserved.

"""Branch views."""

__metaclass__ = type

__all__ = [
    'BranchAddView',
    'BranchContextMenu',
    'BranchDeletionView',
    'BranchEditView',
    'BranchEditWhiteboardView',
    'BranchRequestImportView',
    'BranchReviewerEditView',
    'BranchMergeQueueView',
    'BranchMirrorStatusView',
    'BranchNavigation',
    'BranchNavigationMenu',
    'BranchInProductView',
    'BranchURL',
    'BranchView',
    'BranchSubscriptionsView',
    'RegisterBranchMergeProposalView',
    ]

import cgi
from datetime import datetime, timedelta
import pytz

from zope.app.form.browser import TextAreaWidget
from zope.traversing.interfaces import IPathAdapter
from zope.component import getUtility, queryAdapter
from zope.formlib import form
from zope.interface import Interface, implements
from zope.publisher.interfaces import NotFound
from zope.schema import Choice, Text
from lazr.delegates import delegates
from lazr.enum import EnumeratedType, Item
from lazr.uri import URI

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.database.constants import UTC_NOW

from lazr.restful.interface import copy_field, use_template
from canonical.launchpad import _
from canonical.launchpad.browser.feeds import BranchFeedLink, FeedsMixin
from canonical.launchpad.browser.launchpad import Hierarchy
from canonical.launchpad.helpers import truncate_text
from canonical.launchpad.interfaces.bug import IBugSet
from canonical.launchpad.interfaces.bugbranch import IBugBranch
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.specificationbranch import ISpecificationBranch
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, enabled_with_permission,
    LaunchpadView, Navigation, NavigationMenu, stepto, stepthrough,
    LaunchpadFormView, LaunchpadEditFormView, action, custom_widget)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp.menu import structured
from canonical.widgets.branch import TargetBranchWidget
from canonical.widgets.itemswidgets import LaunchpadRadioWidgetWithDescription

from lp.code.browser.branchref import BranchRef
from lp.code.interfaces.branch import (
    BranchCreationForbidden, BranchExists, BranchType, IBranch,
    IBranchNavigationMenu, UICreatableBranchType)
from lp.code.interfaces.branchmergeproposal import (
    IBranchMergeProposal, InvalidBranchMergeProposal)
from lp.code.interfaces.branchsubscription import IBranchSubscription
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.interfaces.codeimportjob import (
    CodeImportJobState, ICodeImportJobWorkflow)
from lp.code.interfaces.codereviewcomment import ICodeReviewComment
from lp.code.interfaces.branchnamespace import (
    get_branch_namespace, IBranchNamespacePolicy)
from lp.code.interfaces.branchtarget import IHasBranchTarget
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference
from lp.registry.interfaces.person import IPerson, IPersonSet
from lp.registry.interfaces.productseries import IProductSeries


def quote(text):
    return cgi.escape(text, quote=True)


class BranchURL:
    """Branch URL creation rules."""

    implements(ICanonicalUrlData)

    rootsite = 'code'

    def __init__(self, branch):
        self.branch = branch

    @property
    def inside(self):
        return self.branch.owner

    @property
    def path(self):
        return '%s/%s' % (self.branch.target.name, self.branch.name)


class BranchHierarchy(Hierarchy):
    """The hierarchy for a branch should be the product if there is one."""

    def items(self):
        """See `Hierarchy`."""
        return self._breadcrumbs(
            (obj, canonical_url(obj))
            for obj in IHasBranchTarget(self.context).target.components)


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


class BranchNavigationMenu(NavigationMenu):
    """Internal menu tabs."""

    usedfor = IBranchNavigationMenu
    facet = 'branches'
    links = ['details', 'merges', 'source']

    def __init__(self, context):
        NavigationMenu.__init__(self, context)
        if IBranch.providedBy(context):
            self.branch = context
        elif IBranchMergeProposal.providedBy(context):
            self.branch = context.source_branch
            self.disabled = True
        elif IBranchSubscription.providedBy(context):
            self.branch = context.branch
        elif ICodeReviewComment.providedBy(context):
            self.branch = context.branch_merge_proposal.source_branch
            self.disabled = True
        else:
            raise AssertionError(
                'Bad context type for branch navigation menu.')

    def details(self):
        url = canonical_url(self.branch)
        return Link(url, 'Details')

    def merges(self):
        url = canonical_url(self.branch, view_name="+merges")
        return Link(url, 'Merge Proposals')

    def source(self):
        """Return a link to the branch's file listing on codebrowse."""
        text = 'Source Code'
        enabled = self.branch.code_is_browseable
        url = self.branch.codebrowse_url('files')
        return Link(url, text, icon='info', enabled=enabled)


class BranchContextMenu(ContextMenu):
    """Context menu for branches."""

    usedfor = IBranch
    facet = 'branches'
    links = ['whiteboard', 'edit', 'delete_branch', 'browse_revisions',
             'subscription', 'add_subscriber', 'associations',
             'register_merge', 'landing_candidates',
             'link_bug', 'link_blueprint', 'edit_import', 'reviewer'
             ]

    def whiteboard(self):
        text = 'Edit whiteboard'
        return Link('+whiteboard', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change branch details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reviewer(self):
        text = 'Set branch reviewer'
        return Link('+reviewer', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def delete_branch(self):
        text = 'Delete branch'
        return Link('+delete', text)

    def browse_revisions(self):
        """Return a link to the branch's revisions on codebrowse."""
        text = 'All revisions'
        enabled = self.context.code_is_browseable
        url = self.context.codebrowse_url('changes')
        return Link(url, text, enabled=enabled)

    @enabled_with_permission('launchpad.AnyPerson')
    def subscription(self):
        if self.context.hasSubscription(self.user):
            url = '+edit-subscription'
            text = 'Edit your subscription'
            icon = 'edit'
        else:
            url = '+subscribe'
            text = 'Subscribe yourself'
            icon = 'add'
        return Link(url, text, icon=icon)

    @enabled_with_permission('launchpad.AnyPerson')
    def add_subscriber(self):
        text = 'Subscribe someone else'
        return Link('+addsubscriber', text, icon='add')

    def associations(self):
        text = 'View branch associations'
        return Link('+associations', text)

    @enabled_with_permission('launchpad.AnyPerson')
    def register_merge(self):
        text = 'Propose for merging into another branch'
        # It is not valid to propose a junk branch for merging.
        enabled = self.context.product is not None
        return Link('+register-merge', text, icon='add', enabled=enabled)

    def landing_candidates(self):
        text = 'View landing candidates'
        enabled = self.context.landing_candidates.count() > 0
        return Link('+landing-candidates', text, icon='edit', enabled=enabled)

    def link_bug(self):
        if self.context.related_bugs:
            text = 'Link to another bug report'
        else:
            text = 'Link to a bug report'
        return Link('+linkbug', text, icon='add')

    def link_blueprint(self):
        if self.context.spec_links:
            text = 'Link to another blueprint'
        else:
            text = 'Link to a blueprint'
        # Since the blueprints are only related to products, there is no
        # point showing this link if the branch is junk.
        enabled = self.context.product is not None
        return Link('+linkblueprint', text, icon='add', enabled=enabled)

    def edit_import(self):
        text = 'Edit import source or review import'
        return Link('+edit-import', text, icon='edit', enabled=True)


class BranchView(LaunchpadView, FeedsMixin):

    __used_for__ = IBranch

    feed_types = (
        BranchFeedLink,
        )

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

    def owner_is_registrant(self):
        """Is the branch owner the registrant?"""
        return self.context.owner == self.context.registrant

    @property
    def codebrowse_url(self):
        """Return the link to codebrowse for this branch."""
        return self.context.codebrowse_url()

    @property
    def pending_writes(self):
        """Whether or not there are pending writes for this branch."""
        return self.context.pending_writes

    def bzr_download_url(self):
        """Return the generic URL for downloading the branch."""
        if self.user_can_download():
            return self.context.bzr_identity
        else:
            return None

    def bzr_upload_url(self):
        """Return the generic URL for uploading the branch."""
        if self.user_can_upload():
            return self.context.bzr_identity
        else:
            return None

    def edit_link_url(self):
        """Target URL of the Edit link used in the actions portlet."""
        # XXX: DavidAllouche 2005-12-02 bug=5313:
        # That should go away when bug #5313 is fixed.
        linkdata = BranchContextMenu(self.context).edit()
        return '%s/%s' % (canonical_url(self.context), linkdata.target)

    def user_can_upload(self):
        """Whether the user can upload to this branch."""
        return (self.user is not None and
                self.user.inTeam(self.context.owner) and
                self.context.branch_type == BranchType.HOSTED)

    def user_can_download(self):
        """Whether the user can download this branch."""
        return (self.context.branch_type != BranchType.REMOTE and
                self.context.revision_count > 0)

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

    @property
    def latest_landing_candidates(self):
        """Return a decorated filtered list of landing candidates."""
        # Only show the most recent 5 landing_candidates
        return self.landing_candidates[:5]

    @cachedproperty
    def landing_candidates(self):
        """Return a decorated list of landing candidates."""
        candidates = self.context.landing_candidates
        return [DecoratedMergeProposal(proposal) for proposal in candidates]

    def _getBranchCountText(self, count):
        """Help to show user friendly text."""
        if count == 0:
            return 'No branches'
        elif count == 1:
            return '1 branch'
        else:
            return '%s branches' % count

    @cachedproperty
    def dependent_branch_count_text(self):
        branch_count = self.context.dependent_branches.count()
        return self._getBranchCountText(branch_count)

    @cachedproperty
    def landing_candidate_count_text(self):
        branch_count = self.context.landing_candidates.count()
        return self._getBranchCountText(branch_count)

    @cachedproperty
    def dependent_branches(self):
        return list(self.context.dependent_branches)

    @cachedproperty
    def no_merges(self):
        """Return true if there are no pending merges"""
        return (len(self.landing_targets) +
                len(self.landing_candidates) +
                len(self.dependent_branches) == 0)

    @property
    def show_candidate_more_link(self):
        """Only show the link if there are more than five."""
        return len(self.landing_candidates) > 5

    @cachedproperty
    def latest_code_import_results(self):
        """Return the last 10 CodeImportResults."""
        return list(self.context.code_import.results[:10])

    @property
    def svn_url_is_web(self):
        """True if an imported branch's SVN URL is HTTP or HTTPS."""
        # You should only be calling this if it's an SVN code import
        assert self.context.code_import
        assert self.context.code_import.svn_branch_url
        url = self.context.code_import.svn_branch_url
        # https starts with http too!
        return url.startswith("http")

    @property
    def mirror_location(self):
        """Check the mirror location to see if it is a private one."""
        branch = self.context

        # If the user has edit permissions, then show the actual location.
        if check_permission('launchpad.Edit', branch):
            return branch.url

        # XXX: Tim Penhey, 2008-05-30
        # Instead of a configuration hack we should support the users
        # specifying whether or not they want the mirror location
        # hidden or not.  Given that this is a database patch,
        # it isn't going to happen today.
        # See bug 235916
        hosts = config.codehosting.private_mirror_hosts.split(',')
        private_mirror_hosts = [name.strip() for name in hosts]

        uri = URI(branch.url)
        for private_host in private_mirror_hosts:
            if uri.underDomain(private_host):
                return '<private server>'

        return branch.url


class DecoratedMergeProposal:
    """Provide some additional attributes to a normal branch merge proposal.
    """
    delegates(IBranchMergeProposal)

    def __init__(self, context):
        self.context = context

    def show_registrant(self):
        """Show the registrant if it was not the branch owner."""
        return self.context.registrant != self.source_branch.owner


class BranchInProductView(BranchView):

    show_person_link = True
    show_product_link = False


class BranchNameValidationMixin:
    """Provide name validation logic used by several branch view classes."""

    def _setBranchExists(self, existing_branch):
        owner = existing_branch.owner
        if owner == self.user:
            prefix = "You already have"
        else:
            prefix = "%s already has" % cgi.escape(owner.displayname)
        message = (
            "%s a branch for <em>%s</em> called <em>%s</em>."
            % (prefix, existing_branch.target.displayname,
               existing_branch.name))
        self.setFieldError('name', structured(message))


class BranchEditSchema(Interface):
    """Defines the fields for the edit form.

    This is necessary so as to make an editable field for the branch privacy.
    Normally the field is not editable through the interface in order to stop
    direct setting of the private attribute, but in this case we actually want
    the user to be able to edit it.
    """
    use_template(IBranch, include=[
            'owner', 'product', 'name', 'url', 'title', 'summary',
            'lifecycle_status', 'whiteboard'])
    private = copy_field(IBranch['private'], readonly=False)


class BranchEditFormView(LaunchpadEditFormView):
    """Base class for forms that edit a branch."""

    schema = BranchEditSchema
    field_names = None

    @property
    def adapters(self):
        """See `LaunchpadFormView`"""
        return {BranchEditSchema: self.context}

    @action('Change Branch', name='change')
    def change_action(self, action, data):
        # If the owner or product has changed, add an explicit notification.
        if 'owner' in data:
            new_owner = data['owner']
            if new_owner != self.context.owner:
                self.request.response.addNotification(
                    "The branch owner has been changed to %s (%s)"
                    % (new_owner.displayname, new_owner.name))
        if 'product' in data:
            new_product = data['product']
            if new_product != self.context.product:
                if new_product is None:
                    # Branch has been made junk.
                    self.request.response.addNotification(
                        "This branch is no longer associated with a project.")
                else:
                    self.request.response.addNotification(
                        "The project for this branch has been changed to %s "
                        "(%s)" % (new_product.displayname, new_product.name))
        if 'private' in data:
            private = data.pop('private')
            if private != self.context.private:
                # We only want to show notifications if it actually changed.
                self.context.setPrivate(private)
                if private:
                    self.request.response.addNotification(
                        "The branch is now private, and only visible to the "
                        "owner and to subscribers.")
                else:
                    self.request.response.addNotification(
                        "The branch is now publicly accessible.")
        if self.updateContextFromData(data):
            # Only specify that the context was modified if there
            # was in fact a change.
            self.context.date_last_modified = UTC_NOW

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url


class BranchEditWhiteboardView(BranchEditFormView):
    """A view for editing the whiteboard only."""

    field_names = ['whiteboard']


class BranchMirrorStatusView(LaunchpadFormView):
    """This view displays the mirror status of a branch.

    This includes the next mirror time and any failures that may have
    occurred.
    """

    MAXIMUM_STATUS_MESSAGE_LENGTH = 128

    schema = Interface

    field_names = []

    @property
    def show_detailed_error_message(self):
        """Show detailed error message for branch owner and experts."""
        if self.user is None:
            return False
        else:
            celebs = getUtility(ILaunchpadCelebrities)
            return (self.user.inTeam(self.context.owner) or
                    self.user.inTeam(celebs.admin) or
                    self.user.inTeam(celebs.bazaar_experts))

    @property
    def mirror_of_ssh(self):
        """True if this a mirror branch with an sftp or bzr+ssh URL."""
        if not self.context.url:
            return False # not a mirror branch
        uri = URI(self.context.url)
        return uri.scheme in ('sftp', 'bzr+ssh')

    @property
    def in_mirror_queue(self):
        """Is it likely that the branch is being mirrored in the next run of
        the puller?
        """
        return self.context.next_mirror_time < datetime.now(pytz.UTC)

    @property
    def mirror_disabled(self):
        """Has mirroring this branch been disabled?"""
        return self.context.next_mirror_time is None

    @property
    def mirror_failed_once(self):
        """Has there been exactly one failed attempt to mirror this branch?"""
        return self.context.mirror_failures == 1

    @property
    def mirror_status_message(self):
        """A message from a bad scan or pull, truncated for display."""
        message = self.context.mirror_status_message
        if len(message) <= self.MAXIMUM_STATUS_MESSAGE_LENGTH:
            return message
        return truncate_text(
            message, self.MAXIMUM_STATUS_MESSAGE_LENGTH) + ' ...'

    @property
    def show_mirror_failure(self):
        """True if mirror_of_ssh is false and branch mirroring failed."""
        return not self.mirror_of_ssh and self.context.mirror_failures

    @property
    def action_url(self):
        return "%s/+mirror-status" % canonical_url(self.context)

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

    @cachedproperty
    def display_deletion_requirements(self):
        """Normal deletion requirements, indication of permissions.

        :return: A list of tuples of (item, action, reason, allowed)
        """
        reqs = []
        for item, (action, reason) in (
            self.context.deletionRequirements().iteritems()):
            allowed = check_permission('launchpad.Edit', item)
            reqs.append((item, action, reason, allowed))
        return reqs

    @cachedproperty
    def stacked_branches_count(self):
        """Cache a count of the branches stacked on this."""
        return self.context.getStackedBranches().count()

    def stacked_branches_text(self):
        """Cache a count of the branches stacked on this."""
        if self.stacked_branches_count == 1:
            return _('branch')
        else:
            return _('branches')

    def all_permitted(self):
        """Return True if all deletion requirements are permitted, else False.

        Uses display_deletion_requirements as its source data.
        """
        # Not permitted if there are any branches stacked on this.
        if self.stacked_branches_count > 0:
            return False
        return len([item for item, action, reason, allowed in
            self.display_deletion_requirements if not allowed]) == 0

    @action('Delete', name='delete_branch',
            condition=lambda x, y: x.all_permitted())
    def delete_branch_action(self, action, data):
        branch = self.context
        if self.all_permitted():
            # Since the user is going to delete the branch, we need to have
            # somewhere valid to send them next.
            self.next_url = canonical_url(branch.target)
            message = "Branch %s deleted." % branch.unique_name
            self.context.destroySelf(break_references=True)
            self.request.response.addNotification(message)
        else:
            self.request.response.addNotification(
                "This branch cannot be deleted.")
            self.next_url = canonical_url(branch)

    @property
    def branch_deletion_actions(self):
        """Return the branch deletion actions as a zpt-friendly dict.

        The keys are 'delete' and 'alter'; the values are dicts of
        'item', 'reason' and 'allowed'.
        """
        branch = self.context
        row_dict = {'delete': [], 'alter': [], 'break_link': []}
        for item, action, reason, allowed in (
            self.display_deletion_requirements):
            if IBugBranch.providedBy(item):
                action = 'break_link'
            elif ISpecificationBranch.providedBy(item):
                action = 'break_link'
            elif IProductSeries.providedBy(item):
                action = 'break_link'
            row = {'item': item,
                   'reason': reason,
                   'allowed': allowed,
                  }
            row_dict[action].append(row)
        return row_dict

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class BranchEditView(BranchEditFormView, BranchNameValidationMixin):
    """The main branch view for editing the branch attributes."""

    field_names = [
        'owner', 'product', 'name', 'private', 'url', 'summary',
        'lifecycle_status', 'whiteboard']

    custom_widget('lifecycle_status', LaunchpadRadioWidgetWithDescription)

    def setUpFields(self):
        LaunchpadFormView.setUpFields(self)
        # This is to prevent users from converting push/import
        # branches to pull branches.
        branch = self.context
        if branch.branch_type in (BranchType.HOSTED, BranchType.IMPORTED):
            self.form_fields = self.form_fields.omit('url')

        policy = IBranchNamespacePolicy(branch.namespace)
        if branch.private:
            # If the branch is private, and can be public, show the field.
            show_private_field = policy.canBranchesBePublic()
        else:
            # If the branch is public, and can be made private, show the
            # field.
            show_private_field = policy.canBranchesBePrivate()

        if not show_private_field:
            self.form_fields = self.form_fields.omit('private')

        # If the user can administer branches, then they should be able to
        # assign the ownership of the branch to any valid person or team.
        if check_permission('launchpad.Admin', branch):
            owner_field = self.schema['owner']
            any_owner_choice = Choice(
                __name__='owner', title=owner_field.title,
                description = _("As an administrator you are able to reassign"
                                " this branch to any person or team."),
                required=True, vocabulary='ValidPersonOrTeam')
            any_owner_field = form.Fields(
                any_owner_choice, render_context=self.render_context)
            # Replace the normal owner field with a more permissive vocab.
            self.form_fields = self.form_fields.omit('owner')
            self.form_fields = any_owner_field + self.form_fields

    def validate_branch_name(self, owner, product, branch_name):
        # XXX: JonathanLange 2009-03-30 spec=package-branches: Don't look
        # before you leap. Instead try to move the branch and then populate
        # the error field.
        namespace = get_branch_namespace(owner, product=product)
        existing_branch = namespace.getByName(branch_name)
        if existing_branch is not None:
            # There is a branch that has the branch_name specified already.
            self._setBranchExists(existing_branch)

    def validate(self, data):
        # Check that we're not moving a team branch to the +junk
        # pseudo project.
        owner = data['owner']
        if ('product' in data and data['product'] is None
            and (owner is not None and owner.isTeam())):
            self.setFieldError(
                'product',
                "Team-owned branches must be associated with a project.")
        if 'product' in data and 'name' in data:
            # Only validate if the name has changed, or the product has
            # changed, or the owner has changed.
            if ((data['product'] != self.context.product) or
                (data['name'] != self.context.name) or
                (owner != self.context.owner)):
                self.validate_branch_name(owner,
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
                error = self.getFieldError('url')
                if not error:
                    self.setFieldError(
                        'url',
                        'Branch URLs are required for Mirrored branches.')
        else:
            # We don't care about whether the URL is set for REMOTE branches,
            # and the URL field is not shown for IMPORT or HOSTED branches.
            pass


class BranchReviewerEditSchema(Interface):
    """The schema to edit the branch reviewer."""

    reviewer = copy_field(IBranch['reviewer'], required=True)


class BranchReviewerEditView(LaunchpadEditFormView):
    """The view to set the review team."""

    schema = BranchReviewerEditSchema

    @property
    def adapters(self):
        """See `LaunchpadFormView`"""
        return {BranchReviewerEditSchema: self.context}

    @property
    def initial_values(self):
        return {'reviewer': self.context.code_reviewer}

    @action('Save', name='save')
    def save_action(self, action, data):
        """Save the values."""
        reviewer = data['reviewer']
        if reviewer == self.context.code_reviewer:
            # No change, so don't update last modified.
            return

        if reviewer == self.context.owner:
            # Clear the reviewer if set to the same as the owner.
            self.context.reviewer = None
        else:
            self.context.reviewer = reviewer

        self.context.date_last_modified = UTC_NOW

    @property
    def next_url(self):
        return canonical_url(self.context)

    cancel_url = next_url


class BranchAddView(LaunchpadFormView, BranchNameValidationMixin):

    schema = IBranch
    for_input = True
    field_names = ['owner', 'name', 'branch_type', 'url',
                   'summary', 'lifecycle_status', 'whiteboard']

    branch = None
    custom_widget('branch_type', LaunchpadRadioWidgetWithDescription)
    custom_widget('lifecycle_status', LaunchpadRadioWidgetWithDescription)

    initial_focus_widget = 'name'

    @property
    def initial_values(self):
        return {
            'owner': self.default_owner,
            'branch_type': UICreatableBranchType.MIRRORED}

    @property
    def target(self):
        """The branch target for the context."""
        return IBranchTarget(self.context)

    @property
    def default_owner(self):
        """The default owner of branches in this context.

        If the context is a person, then it's the context. If the context is
        not a person, then the default owner is the currently logged-in user.
        """
        return IPerson(self.context, self.user)

    def showOptionalMarker(self, field_name):
        """Don't show the optional marker for url."""
        if field_name == 'url':
            return False
        else:
            return LaunchpadFormView.showOptionalMarker(self, field_name)

    @action('Register Branch', name='add')
    def add_action(self, action, data):
        """Handle a request to create a new branch for this product."""
        try:
            ui_branch_type = data['branch_type']
            namespace = self.target.getNamespace(data['owner'])
            self.branch = namespace.createBranch(
                branch_type=BranchType.items[ui_branch_type.name],
                name=data['name'],
                registrant=self.user,
                url=data.get('url'),
                summary=data['summary'],
                lifecycle_status=data['lifecycle_status'],
                whiteboard=data['whiteboard'])
            if self.branch.branch_type == BranchType.MIRRORED:
                self.branch.requestMirror()
        except BranchCreationForbidden:
            self.addError(
                "You are not allowed to create branches in %s." %
                self.context.displayname)
        except BranchExists, e:
            self._setBranchExists(e.existing_branch)
        else:
            self.next_url = canonical_url(self.branch)

    def validate(self, data):
        owner = data['owner']

        if not self.user.inTeam(owner):
            self.setFieldError(
                'owner',
                'You are not a member of %s' % owner.displayname)

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
                error = self.getFieldError('url')
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

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class DecoratedSubscription:
    """Adds the editable attribute to a `BranchSubscription`."""
    delegates(IBranchSubscription, 'subscription')

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
        celebs = getUtility(ILaunchpadCelebrities)
        return (self.user.inTeam(subscription.person) or
                self.user.inTeam(celebs.admin) or
                self.user.inTeam(celebs.bazaar_experts))

    def subscriptions(self):
        """Return a decorated list of branch subscriptions."""
        sorted_subscriptions = sorted(
            self.context.subscriptions,
            key=lambda subscription: subscription.person.browsername)
        return [DecoratedSubscription(
                    subscription, self.isEditable(subscription))
                for subscription in sorted_subscriptions]

    def owner_is_registrant(self):
        """Return whether or not owner is the same as the registrant"""
        return self.context.owner == self.context.registrant


class BranchMergeQueueView(LaunchpadView):
    """The view used to render the merge queue for a branch."""

    __used_for__ = IBranch

    @cachedproperty
    def merge_queue(self):
        """Get the merge queue and check visibility."""
        result = []
        for proposal in self.context.getMergeQueue():
            # If the logged in user cannot view the proposal then we
            # show a "place holder" in the queue position.
            if check_permission('launchpad.View', proposal):
                result.append(proposal)
            else:
                result.append(None)
        return result


class RegisterProposalStatus(EnumeratedType):
    """A restricted status enum for the register proposal form."""

    # The text in this enum is different from the general proposal status
    # enum as we want the help text that is shown in the form to be more
    # relevant to the registration of the proposal.

    NEEDS_REVIEW = Item("""
        Needs review

        The changes are ready for review.
        """)

    WORK_IN_PROGRESS = Item("""
        Work in progress

        The changes are still being actively worked on, and are not
        yet ready for review.
        """)


class RegisterProposalSchema(Interface):
    """The schema to define the form for registering a new merge proposal."""
    target_branch = Choice(
        title=_('Target Branch'),
        vocabulary='BranchRestrictedOnProduct', required=True, readonly=True,
        description=_(
            "The branch that the source branch will be merged into."))

    comment = Text(
        title=_('Initial Comment'), required=False,
        description=_('Describe your change.'))

    reviewer = copy_field(
        ICodeReviewVoteReference['reviewer'], required=False)

    review_type = copy_field(ICodeReviewVoteReference['review_type'])


class RegisterBranchMergeProposalView(LaunchpadFormView):
    """The view to register new branch merge proposals."""
    schema = RegisterProposalSchema
    for_input = True

    custom_widget('target_branch', TargetBranchWidget)
    custom_widget('comment', TextAreaWidget, cssClass='codereviewcomment')

    @property
    def initial_values(self):
        """The default reviewer is the code reviewer of the target."""
        # If there is a development focus branch for the product, then default
        # the reviewer to be the review team for that branch.
        reviewer = None
        dev_focus_branch = self.context.product.development_focus.branch
        if dev_focus_branch is not None:
            reviewer = dev_focus_branch.code_reviewer
        return {'reviewer': reviewer}

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def initialize(self):
        """Show a 404 if the source branch is junk."""
        if self.context.product is None:
            raise NotFound(self.context, '+register-merge')
        LaunchpadFormView.initialize(self)

    @action('Propose Merge', name='register')
    def register_action(self, action, data):
        """Register the new branch merge proposal."""

        registrant = self.user
        source_branch = self.context
        target_branch = data['target_branch']

        review_requests = []
        reviewer = data.get('reviewer')
        if reviewer is not None:
            review_requests.append((reviewer, data.get('review_type')))

        try:
            # Always default to needs review until we have the wonder of AJAX
            # and an advanced expandable section.
            proposal = source_branch.addLandingTarget(
                registrant=registrant, target_branch=target_branch,
                needs_review=True, initial_comment=data.get('comment'),
                review_requests=review_requests)

            self.next_url = canonical_url(proposal)
        except InvalidBranchMergeProposal, error:
            self.addError(str(error))

    def validate(self, data):
        source_branch = self.context
        target_branch = data.get('target_branch')

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


class BranchRequestImportView(LaunchpadFormView):
    """The view to provide an 'Import now' button on the branch index page.

    This only appears on the page of a branch with an associated code import
    that is being actively imported and where there is a import scheduled at
    some point in the future.
    """

    schema = IBranch
    field_names = []

    form_style = "display: inline"

    @property
    def next_url(self):
        return canonical_url(self.context)

    @action('Import Now', name='request')
    def request_import_action(self, action, data):
        if self.context.code_import.import_job is None:
            self.request.response.addNotification(
                "This import is no longer being updated automatically.")
        elif self.context.code_import.import_job.state != \
                 CodeImportJobState.PENDING:
            assert self.context.code_import.import_job.state == \
                   CodeImportJobState.RUNNING
            self.request.response.addNotification(
                "The import is already running.")
        elif self.context.code_import.import_job.requesting_user is not None:
            user = self.context.code_import.import_job.requesting_user
            adapter = queryAdapter(user, IPathAdapter, 'fmt')
            self.request.response.addNotification(
                structured("The import has already been requested by %s." %
                           adapter.link(None)))
        else:
            getUtility(ICodeImportJobWorkflow).requestJob(
                self.context.code_import.import_job, self.user)
            self.request.response.addNotification(
                "Import will run as soon as possible.")

    @property
    def prefix(self):
        return "request%s" % self.context.id

    @property
    def action_url(self):
        return "%s/@@+request-import" % canonical_url(self.context)
