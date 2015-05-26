# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository views."""

__metaclass__ = type

__all__ = [
    'GitRefBatchNavigator',
    'GitRepositoryBreadcrumb',
    'GitRepositoryContextMenu',
    'GitRepositoryDeletionView',
    'GitRepositoryEditMenu',
    'GitRepositoryNavigation',
    'GitRepositoryURL',
    'GitRepositoryView',
    ]

from storm.expr import Desc
from zope.interface import implements

from lp.app.browser.informationtype import InformationTypePortletMixin
from lp.app.browser.launchpadform import (
    action,
    LaunchpadFormView,
    )
from lp.app.errors import NotFoundError
from lp.code.interfaces.gitref import IGitRefBatchNavigator
from lp.code.interfaces.gitrepository import IGitRepository
from lp.services.config import config
from lp.services.propertycache import cachedproperty
from lp.services.webapp import (
    canonical_url,
    ContextMenu,
    enabled_with_permission,
    LaunchpadView,
    Link,
    Navigation,
    NavigationMenu,
    stepthrough,
    stepto,
    )
from lp.services.webapp.authorization import (
    check_permission,
    precache_permission_for_objects,
    )
from lp.services.webapp.batching import TableBatchNavigator
from lp.services.webapp.breadcrumb import NameBreadcrumb
from lp.services.webapp.interfaces import ICanonicalUrlData


class GitRepositoryURL:
    """Git repository URL creation rules."""

    implements(ICanonicalUrlData)

    rootsite = "code"
    inside = None

    def __init__(self, repository):
        self.repository = repository

    @property
    def path(self):
        return self.repository.unique_name


class GitRepositoryBreadcrumb(NameBreadcrumb):

    @property
    def inside(self):
        return self.context.unique_name.split("/")[-1]


class GitRepositoryNavigation(Navigation):

    usedfor = IGitRepository

    @stepto("+ref")
    def traverse_ref(self):
        segments = list(self.request.getTraversalStack())
        ref_segments = []
        while segments:
            ref_segments.append(segments.pop())
            ref = self.context.getRefByPath("/".join(ref_segments))
            if ref is not None:
                for _ in range(len(ref_segments)):
                    self.request.stepstogo.consume()
                return ref
        raise NotFoundError

    @stepthrough("+merge")
    def traverse_merge_proposal(self, id):
        """Traverse to an `IBranchMergeProposal`."""
        try:
            id = int(id)
        except ValueError:
            # Not a number.
            return None
        return self.context.getMergeProposalByID(id)


class GitRepositoryEditMenu(NavigationMenu):
    """Edit menu for `IGitRepository`."""

    usedfor = IGitRepository
    facet = "branches"
    title = "Edit Git repository"
    links = ["delete"]

    @enabled_with_permission("launchpad.Edit")
    def delete(self):
        text = "Delete repository"
        return Link("+delete", text, icon="trash-icon")


class GitRepositoryContextMenu(ContextMenu):
    """Context menu for `IGitRepository`."""

    usedfor = IGitRepository
    facet = "branches"
    links = ["add_subscriber", "source", "subscription"]

    @enabled_with_permission("launchpad.AnyPerson")
    def subscription(self):
        if self.context.hasSubscription(self.user):
            url = "+edit-subscription"
            text = "Edit your subscription"
            icon = "edit"
        else:
            url = "+subscribe"
            text = "Subscribe yourself"
            icon = "add"
        return Link(url, text, icon=icon)

    @enabled_with_permission("launchpad.AnyPerson")
    def add_subscriber(self):
        text = "Subscribe someone else"
        return Link("+addsubscriber", text, icon="add")

    def source(self):
        """Return a link to the branch's browsing interface."""
        text = "Browse the code"
        url = self.context.getCodebrowseUrl()
        return Link(url, text, icon="info")


class GitRefBatchNavigator(TableBatchNavigator):
    """Batch up the branch listings."""
    implements(IGitRefBatchNavigator)

    def __init__(self, view, context):
        self.context = context
        super(GitRefBatchNavigator, self).__init__(
            self._branches, view.request,
            size=config.launchpad.branchlisting_batch_size)
        self.view = view
        self.column_count = 3

    @property
    def _branches(self):
        from lp.code.model.gitref import GitRef
        return self.context.branches.order_by(Desc(GitRef.committer_date))

    @property
    def table_class(self):
        # XXX: MichaelHudson 2007-10-18 bug=153894: This means there are two
        # ways of sorting a one-page branch listing, which is confusing and
        # incoherent.
        if self.has_multiple_pages:
            return "listing"
        else:
            return "listing sortable"


class GitRepositoryView(InformationTypePortletMixin, LaunchpadView):

    @property
    def page_title(self):
        return self.context.display_name

    label = page_title

    def initialize(self):
        super(GitRepositoryView, self).initialize()
        # Cache permission so that the private team owner can be rendered.  The
        # security adapter will do the job also but we don't want or need the
        # expense of running several complex SQL queries.
        authorised_people = [self.context.owner]
        if self.user is not None:
            precache_permission_for_objects(
                self.request, "launchpad.LimitedView", authorised_people)

    @property
    def user_can_push(self):
        """Whether the user can push to this branch."""
        return check_permission("launchpad.Edit", self.context)

    def branches(self):
        """All branches in this repository, sorted for display."""
        return GitRefBatchNavigator(self, self.context)


class GitRepositoryDeletionView(LaunchpadFormView):

    schema = IGitRepository
    field_names = []

    @property
    def page_title(self):
        return "Delete repository %s" % self.context.display_name

    label = page_title

    @cachedproperty
    def display_deletion_requirements(self):
        """Normal deletion requirements, indication of permissions.

        :return: A list of tuples of (item, action, reason, allowed)
        """
        reqs = []
        for item, (action, reason) in (
                self.context.getDeletionRequirements().iteritems()):
            allowed = check_permission("launchpad.Edit", item)
            reqs.append((item, action, reason, allowed))
        return reqs

    def all_permitted(self):
        """Return True if all deletion requirements are permitted, else False.

        Uses display_deletion_requirements as its source data.
        """
        return len([item for item, action, reason, allowed in
            self.display_deletion_requirements if not allowed]) == 0

    @action("Delete", name="delete_repository",
            condition=lambda x, _: x.all_permitted())
    def delete_repository_action(self, action, data):
        repository = self.context
        if self.all_permitted():
            # Since the user is going to delete the repository, we need to
            # have somewhere valid to send them next.
            self.next_url = canonical_url(repository.target)
            message = "Repository %s deleted." % repository.unique_name
            self.context.destroySelf(break_references=True)
            self.request.response.addNotification(message)
        else:
            self.request.response.addNotification(
                "This repository cannot be deleted.")
            self.next_url = canonical_url(repository)

    @property
    def repository_deletion_actions(self):
        """Return the repository deletion actions as a ZPT-friendly dict.

        The keys are "delete" and "alter"; the values are dicts of
        "item", "reason" and "allowed".
        """
        row_dict = {"delete": [], "alter": []}
        for item, action, reason, allowed in (
            self.display_deletion_requirements):
            row = {"item": item,
                   "reason": reason,
                   "allowed": allowed,
                  }
            row_dict[action].append(row)
        return row_dict

    @property
    def cancel_url(self):
        return canonical_url(self.context)
