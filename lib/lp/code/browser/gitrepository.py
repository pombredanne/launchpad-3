# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository views."""

__metaclass__ = type

__all__ = [
    'GitRefBatchNavigator',
    'GitRepositoriesBreadcrumb',
    'GitRepositoryBreadcrumb',
    'GitRepositoryContextMenu',
    'GitRepositoryDeletionView',
    'GitRepositoryEditInformationTypeView',
    'GitRepositoryEditMenu',
    'GitRepositoryEditReviewerView',
    'GitRepositoryEditView',
    'GitRepositoryNavigation',
    'GitRepositoryURL',
    'GitRepositoryView',
    ]

from lazr.lifecycle.event import ObjectModifiedEvent
from lazr.lifecycle.snapshot import Snapshot
from lazr.restful.interface import (
    copy_field,
    use_template,
    )
from six.moves.urllib_parse import (
    urlsplit,
    urlunsplit,
    )
from zope.component import getUtility
from zope.event import notify
from zope.formlib import form
from zope.interface import (
    implementer,
    Interface,
    providedBy,
    )
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.schema import Choice
from zope.schema.vocabulary import (
    SimpleTerm,
    SimpleVocabulary,
    )

from lp import _
from lp.app.browser.informationtype import InformationTypePortletMixin
from lp.app.browser.launchpadform import (
    action,
    LaunchpadEditFormView,
    LaunchpadFormView,
    )
from lp.app.errors import NotFoundError
from lp.app.vocabularies import InformationTypeVocabulary
from lp.app.widgets.itemswidgets import LaunchpadRadioWidgetWithDescription
from lp.code.browser.branch import CodeEditOwnerMixin
from lp.code.browser.branchmergeproposal import (
    latest_proposals_for_each_branch,
    )
from lp.code.browser.codeimport import CodeImportTargetMixin
from lp.code.browser.sourcepackagerecipelisting import HasRecipesMenuMixin
from lp.code.browser.widgets.gitrepositorytarget import (
    GitRepositoryTargetDisplayWidget,
    GitRepositoryTargetWidget,
    )
from lp.code.enums import GitRepositoryType
from lp.code.errors import (
    GitDefaultConflict,
    GitRepositoryCreationForbidden,
    GitRepositoryExists,
    GitTargetError,
    )
from lp.code.interfaces.gitnamespace import get_git_namespace
from lp.code.interfaces.gitref import IGitRefBatchNavigator
from lp.code.interfaces.gitrepository import IGitRepository
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    )
from lp.registry.vocabularies import UserTeamsParticipationPlusSelfVocabulary
from lp.services.config import config
from lp.services.database.constants import UTC_NOW
from lp.services.features import getFeatureFlag
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
from lp.services.webapp.breadcrumb import Breadcrumb
from lp.services.webapp.escaping import structured
from lp.services.webapp.interfaces import ICanonicalUrlData
from lp.services.webapp.publisher import DataDownloadView
from lp.services.webhooks.browser import WebhookTargetNavigationMixin
from lp.snappy.browser.hassnaps import HasSnapsViewMixin


@implementer(ICanonicalUrlData)
class GitRepositoryURL:
    """Git repository URL creation rules."""

    rootsite = "code"
    inside = None

    def __init__(self, repository):
        self.repository = repository

    @property
    def path(self):
        return self.repository.unique_name


class GitRepositoriesBreadcrumb(Breadcrumb):

    text = "Git"

    @property
    def url(self):
        return canonical_url(self.context, view_name="+git")

    @property
    def inside(self):
        return self.context


class GitRepositoryBreadcrumb(Breadcrumb):

    @property
    def text(self):
        return self.context.git_identity

    @property
    def inside(self):
        return GitRepositoriesBreadcrumb(self.context.target)


class GitRepositoryNavigation(WebhookTargetNavigationMixin, Navigation):

    usedfor = IGitRepository

    @stepto("+ref")
    def traverse_ref(self):
        segments = list(self.request.getTraversalStack())
        ref_segments = []
        while segments:
            ref_segments.append(segments.pop())
            ref = self.context.getRefByPath("/".join(ref_segments))
            if ref is not None:
                for unused in range(len(ref_segments)):
                    self.request.stepstogo.consume()
                return ref
        raise NotFoundError

    @stepthrough("+subscription")
    def traverse_subscription(self, name):
        """Traverses to an `IGitSubscription`."""
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
        return self.context.getMergeProposalByID(id)

    @stepto("+diff")
    def traverse_diff(self):
        segments = list(self.request.getTraversalStack())
        if len(segments) == 1:
            new = segments.pop()
            old = new + "^"
            self.request.stepstogo.consume()
        elif len(segments) == 2:
            new = segments.pop()
            old = segments.pop()
            self.request.stepstogo.consume()
            self.request.stepstogo.consume()
        else:
            return None
        return GitRepositoryDiffView(self.context, self.request, old, new)

    @stepto("+code-import")
    def traverse_code_import(self):
        """Traverses to the `ICodeImport` for the repository."""
        return self.context.code_import


class GitRepositoryEditMenu(NavigationMenu):
    """Edit menu for `IGitRepository`."""

    usedfor = IGitRepository
    facet = "branches"
    title = "Edit Git repository"
    links = ["edit", "reviewer", "webhooks", "delete"]

    @enabled_with_permission("launchpad.Edit")
    def edit(self):
        text = "Change repository details"
        return Link("+edit", text, icon="edit")

    @enabled_with_permission("launchpad.Edit")
    def reviewer(self):
        text = "Set repository reviewer"
        return Link("+reviewer", text, icon="edit")

    @enabled_with_permission("launchpad.Edit")
    def webhooks(self):
        text = "Manage webhooks"
        return Link(
            "+webhooks", text, icon="edit",
            enabled=bool(getFeatureFlag('webhooks.new.enabled')))

    @enabled_with_permission("launchpad.Edit")
    def delete(self):
        text = "Delete repository"
        return Link("+delete", text, icon="trash-icon")


class GitRepositoryContextMenu(ContextMenu, HasRecipesMenuMixin):
    """Context menu for `IGitRepository`."""

    usedfor = IGitRepository
    facet = "branches"
    links = [
        "add_subscriber", "create_recipe", "edit_import", "source",
        "subscription", "view_recipes", "visibility"]

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
        """Return a link to the repository's browsing interface."""
        text = "Browse the code"
        url = self.context.getCodebrowseUrl()
        return Link(url, text, icon="info")

    @enabled_with_permission("launchpad.Edit")
    def visibility(self):
        """Return the "Change information type" Link."""
        text = "Change information type"
        return Link("+edit-information-type", text)

    def edit_import(self):
        text = "Edit import source or review import"
        enabled = (
            self.context.repository_type == GitRepositoryType.IMPORTED and
            check_permission("launchpad.Edit", self.context.code_import))
        return Link("+edit-import", text, icon="edit", enabled=enabled)

    def create_recipe(self):
        # You can't create a recipe for a private repository.
        enabled = not self.context.private
        text = "Create packaging recipe"
        return Link("+new-recipe", text, enabled=enabled, icon="add")


@implementer(IGitRefBatchNavigator)
class GitRefBatchNavigator(TableBatchNavigator):
    """Batch up the branch listings."""

    def __init__(self, view, context):
        self.context = context
        super(GitRefBatchNavigator, self).__init__(
            self.context.branches_by_date, view.request,
            size=config.launchpad.branchlisting_batch_size)
        self.view = view
        self.column_count = 3

    @property
    def table_class(self):
        # XXX: MichaelHudson 2007-10-18 bug=153894: This means there are two
        # ways of sorting a one-page branch listing, which is confusing and
        # incoherent.
        if self.has_multiple_pages:
            return "listing"
        else:
            return "listing sortable"


class GitRepositoryView(InformationTypePortletMixin, LaunchpadView,
                        HasSnapsViewMixin, CodeImportTargetMixin):

    @property
    def page_title(self):
        return self.context.display_name

    label = page_title
    show_merge_links = True

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
    def git_ssh_url(self):
        """The git+ssh:// URL for this repository, adjusted for this user."""
        base_url = urlsplit(self.context.git_ssh_url)
        url = list(base_url)
        url[1] = "{}@{}".format(self.user.name, base_url.hostname)
        return urlunsplit(url)

    @property
    def user_can_push(self):
        """Whether the user can push to this branch."""
        return (
            self.context.repository_type == GitRepositoryType.HOSTED and
            check_permission("launchpad.Edit", self.context))

    def branches(self):
        """All branches in this repository, sorted for display."""
        return GitRefBatchNavigator(self, self.context)

    @property
    def recipes_link(self):
        """A link to recipes for this repository."""
        count = self.context.recipes.count()
        if count == 0:
            # Nothing to link to.
            return 'No recipes using this repository.'
        elif count == 1:
            # Link to the single recipe.
            return structured(
                '<a href="%s">1 recipe</a> using this repository.',
                canonical_url(self.context.recipes.one())).escapedtext
        else:
            # Link to a recipe listing.
            return structured(
                '<a href="+recipes">%s recipes</a> using this repository.',
                count).escapedtext

    @property
    def is_imported(self):
        """Is this an imported repository?"""
        return self.context.repository_type == GitRepositoryType.IMPORTED

    @cachedproperty
    def landing_candidates(self):
        candidates = self.context.getPrecachedLandingCandidates(self.user)
        return [proposal for proposal in candidates
                if check_permission("launchpad.View", proposal)]

    def _getBranchCountText(self, count):
        """Help to show user friendly text."""
        if count == 0:
            return 'No branches'
        elif count == 1:
            return '1 branch'
        else:
            return '%s branches' % count

    @cachedproperty
    def landing_candidate_count_text(self):
        return self._getBranchCountText(len(self.landing_candidates))

    @cachedproperty
    def landing_targets(self):
        """Return a filtered list of landing targets."""
        targets = self.context.getPrecachedLandingTargets(self.user)
        return latest_proposals_for_each_branch(targets)


class GitRepositoryEditFormView(LaunchpadEditFormView):
    """Base class for forms that edit a Git repository."""

    field_names = None

    def getInformationTypesToShow(self):
        """Get the information types to display on the edit form.

        We display a customised set of information types: anything allowed
        by the repository's model, plus the current type.
        """
        allowed_types = set(self.context.getAllowedInformationTypes(self.user))
        allowed_types.add(self.context.information_type)
        return allowed_types

    @cachedproperty
    def schema(self):
        info_types = self.getInformationTypesToShow()

        class GitRepositoryEditSchema(Interface):
            """Defines the fields for the edit form.

            This is necessary to make various fields editable that are not
            normally editable through the interface.
            """
            use_template(IGitRepository, include=["default_branch"])
            information_type = copy_field(
                IGitRepository["information_type"], readonly=False,
                vocabulary=InformationTypeVocabulary(types=info_types))
            name = copy_field(IGitRepository["name"], readonly=False)
            owner = copy_field(IGitRepository["owner"], readonly=False)
            owner_default = copy_field(
                IGitRepository["owner_default"], readonly=False)
            reviewer = copy_field(IGitRepository["reviewer"], required=True)
            target = copy_field(IGitRepository["target"], readonly=False)

        return GitRepositoryEditSchema

    @property
    def page_title(self):
        return "Edit %s" % self.context.display_name

    @property
    def label(self):
        return self.page_title

    @property
    def adapters(self):
        """See `LaunchpadFormView`."""
        return {self.schema: self.context}

    @action("Change Git Repository", name="change",
            failure=LaunchpadFormView.ajax_failure_handler)
    def change_action(self, action, data):
        # If the owner has changed, add an explicit notification.  We take
        # our own snapshot here to make sure that the snapshot records
        # changes to the owner, and we notify the listeners explicitly below
        # rather than the notification that would normally be sent in
        # updateContextFromData.
        changed = False
        repository_before_modification = Snapshot(
            self.context, providing=providedBy(self.context))
        if "name" in data:
            name = data.pop("name")
            if name != self.context.name:
                self.context.setName(name, self.user)
                changed = True
        if "owner" in data:
            owner = data.pop("owner")
            if owner != self.context.owner:
                self.context.setOwner(owner, self.user)
                changed = True
                self.request.response.addNotification(
                    "The repository owner has been changed to %s (%s)" %
                    (owner.displayname, owner.name))
        if "information_type" in data:
            information_type = data.pop("information_type")
            self.context.transitionToInformationType(
                information_type, self.user)
        if "target" in data:
            target = data.pop("target")
            if target is None:
                target = self.context.owner
            if target != self.context.target:
                try:
                    self.context.setTarget(target, self.user)
                except GitTargetError as e:
                    self.setFieldError("target", e.message)
                    return
                changed = True
                if IPerson.providedBy(target):
                    self.request.response.addNotification(
                        "This repository is now a personal repository for %s "
                        "(%s)" % (target.displayname, target.name))
                else:
                    self.request.response.addNotification(
                        "The repository target has been changed to %s (%s)" %
                        (target.displayname, target.name))
        if "reviewer" in data:
            reviewer = data.pop("reviewer")
            if reviewer != self.context.code_reviewer:
                if reviewer == self.context.owner:
                    # Clear the reviewer if set to the same as the owner.
                    self.context.reviewer = None
                else:
                    self.context.reviewer = reviewer
                changed = True
        if "owner_default" in data:
            owner_default = data.pop("owner_default")
            if (self.context.namespace.has_defaults and
                    owner_default != self.context.owner_default):
                self.context.setOwnerDefault(owner_default)

        if self.updateContextFromData(data, notify_modified=False):
            changed = True

        if changed:
            # Notify that the object has changed with the snapshot that was
            # taken earlier.
            field_names = [
                form_field.__name__ for form_field in self.form_fields]
            notify(ObjectModifiedEvent(
                self.context, repository_before_modification, field_names))
            # Only specify that the context was modified if there
            # was in fact a change.
            self.context.date_last_modified = UTC_NOW

        if self.request.is_ajax:
            return ""

    @property
    def next_url(self):
        """Return the next URL to call when this call completes."""
        if not self.request.is_ajax and not self.errors:
            return self.cancel_url
        return None

    @property
    def cancel_url(self):
        return canonical_url(self.context)


class GitRepositoryEditInformationTypeView(GitRepositoryEditFormView):
    """A view to set the information type."""

    field_names = ["information_type"]


class GitRepositoryEditReviewerView(GitRepositoryEditFormView):
    """A view to set the review team."""

    field_names = ["reviewer"]

    @property
    def initial_values(self):
        return {"reviewer": self.context.code_reviewer}


class GitRepositoryEditView(CodeEditOwnerMixin, GitRepositoryEditFormView):
    """The main view for editing repository attributes."""

    field_names = [
        "owner",
        "name",
        "target",
        "information_type",
        "owner_default",
        "default_branch",
        ]

    custom_widget_information_type = LaunchpadRadioWidgetWithDescription

    any_owner_description = _(
        "As an administrator you are able to assign this repository to any "
        "person or team.")

    def setUpFields(self):
        super(GitRepositoryEditView, self).setUpFields()
        repository = self.context
        # If the user can administer repositories, then they should be able
        # to assign the ownership of the repository to any valid person or
        # team.
        if check_permission("launchpad.Admin", repository):
            owner_field = self.schema["owner"]
            any_owner_choice = Choice(
                __name__="owner", title=owner_field.title,
                description=_(
                    "As an administrator you are able to assign this "
                    "repository to any person or team."),
                required=True, vocabulary="ValidPersonOrTeam")
            any_owner_field = form.Fields(
                any_owner_choice, render_context=self.render_context)
            # Replace the normal owner field with a more permissive vocab.
            self.form_fields = self.form_fields.omit("owner")
            self.form_fields = any_owner_field + self.form_fields
        else:
            # For normal users, there are some cases (e.g. package
            # repositories) where the editor may not be in the team of the
            # repository owner.  In these cases we need to extend the
            # vocabulary connected to the owner field.
            if not self.user.inTeam(self.context.owner):
                vocab = UserTeamsParticipationPlusSelfVocabulary()
                owner = self.context.owner
                terms = [SimpleTerm(
                    owner, owner.name, owner.unique_displayname)]
                terms.extend([term for term in vocab])
                owner_field = self.schema["owner"]
                owner_choice = Choice(
                    __name__="owner", title=owner_field.title,
                    description=owner_field.description,
                    required=True, vocabulary=SimpleVocabulary(terms))
                new_owner_field = form.Fields(
                    owner_choice, render_context=self.render_context)
                # Replace the normal owner field with a more permissive vocab.
                self.form_fields = self.form_fields.omit("owner")
                self.form_fields = new_owner_field + self.form_fields
        # If this is the target default, then the target is read-only.
        target_field = self.form_fields.get("target")
        if self.context.target_default:
            target_field.for_display = True
            target_field.custom_widget = GitRepositoryTargetDisplayWidget
        else:
            target_field.custom_widget = GitRepositoryTargetWidget

    def setUpWidgets(self, context=None):
        super(GitRepositoryEditView, self).setUpWidgets(context=context)
        if self.context.target_default:
            self.widgets["target"].hint = (
                "This is the default repository for this target, so it "
                "cannot be moved to another target.")

    def _setRepositoryExists(self, existing_repository, field_name="name"):
        owner = existing_repository.owner
        if owner == self.user:
            prefix = "You already have"
        else:
            prefix = "%s already has" % owner.displayname
        message = structured(
            "%s a repository for <em>%s</em> called <em>%s</em>.",
            prefix, existing_repository.target.displayname,
            existing_repository.name)
        self.setFieldError(field_name, message)

    def validate(self, data):
        if "name" in data and "owner" in data and "target" in data:
            name = data["name"]
            owner = data["owner"]
            target = data["target"]
            if target is None:
                target = owner
            if (name != self.context.name or
                    owner != self.context.owner or
                    target != self.context.target):
                namespace = get_git_namespace(target, owner)
                try:
                    namespace.validateMove(self.context, self.user, name=name)
                except GitRepositoryCreationForbidden:
                    self.addError(
                        "%s is not allowed to own Git repositories in %s." %
                        (owner.displayname, target.displayname))
                except GitRepositoryExists as e:
                    self._setRepositoryExists(e.existing_repository)
                except GitDefaultConflict as e:
                    self.addError(str(e))
        if (self.context.target_default and "target" in data and
                data["target"] != self.context.target):
            self.setFieldError(
                "target",
                "The default repository for a target cannot be moved to "
                "another target.")
        if "default_branch" in data:
            default_branch = data["default_branch"]
            if (default_branch is not None and
                    self.context.getRefByPath(default_branch) is None):
                self.setFieldError(
                    "default_branch",
                    "This repository does not contain a reference named "
                    "'%s'." % default_branch)


@implementer(IBrowserPublisher)
class GitRepositoryDiffView(DataDownloadView):

    content_type = "text/x-patch"
    charset = "UTF-8"

    def __init__(self, context, request, old, new):
        super(GitRepositoryDiffView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.old = old
        self.new = new

    @property
    def filename(self):
        return "%s_%s_%s.diff" % (self.context.name, self.old, self.new)

    def getBody(self):
        return self.context.getDiff(self.old, self.new)

    def browserDefault(self, request):
        return self, ()


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
