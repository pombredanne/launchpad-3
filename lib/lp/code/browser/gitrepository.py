# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository views."""

__metaclass__ = type

__all__ = [
    'GitRefBatchNavigator',
    'GitRepositoriesBreadcrumb',
    'GitRepositoryActivityView',
    'GitRepositoryBreadcrumb',
    'GitRepositoryContextMenu',
    'GitRepositoryDeletionView',
    'GitRepositoryEditInformationTypeView',
    'GitRepositoryEditMenu',
    'GitRepositoryEditReviewerView',
    'GitRepositoryEditView',
    'GitRepositoryNavigation',
    'GitRepositoryPermissionsView',
    'GitRepositoryURL',
    'GitRepositoryView',
    ]

import base64

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
from zope.formlib.textwidgets import IntWidget
from zope.formlib.widget import CustomWidgetFactory
from zope.interface import (
    implementer,
    Interface,
    providedBy,
    )
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.schema import (
    Bool,
    Choice,
    Int,
    )
from zope.schema.vocabulary import (
    getVocabularyRegistry,
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
from lp.app.errors import (
    NotFoundError,
    UnexpectedFormData,
    )
from lp.app.vocabularies import InformationTypeVocabulary
from lp.app.widgets.itemswidgets import LaunchpadRadioWidgetWithDescription
from lp.code.browser.branch import CodeEditOwnerMixin
from lp.code.browser.branchmergeproposal import (
    latest_proposals_for_each_branch,
    )
from lp.code.browser.codeimport import CodeImportTargetMixin
from lp.code.browser.sourcepackagerecipelisting import HasRecipesMenuMixin
from lp.code.browser.widgets.gitgrantee import (
    GitGranteeDisplayWidget,
    GitGranteeField,
    GitGranteeWidget,
    )
from lp.code.browser.widgets.gitrepositorytarget import (
    GitRepositoryTargetDisplayWidget,
    GitRepositoryTargetWidget,
    )
from lp.code.enums import (
    GitGranteeType,
    GitRepositoryType,
    )
from lp.code.errors import (
    GitDefaultConflict,
    GitRepositoryCreationForbidden,
    GitRepositoryExists,
    GitTargetError,
    )
from lp.code.interfaces.gitnamespace import get_git_namespace
from lp.code.interfaces.gitref import IGitRefBatchNavigator
from lp.code.interfaces.gitrepository import IGitRepository
from lp.code.vocabularies.gitrule import GitPermissionsVocabulary
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    )
from lp.registry.vocabularies import UserTeamsParticipationPlusSelfVocabulary
from lp.services.config import config
from lp.services.database.constants import UTC_NOW
from lp.services.features import getFeatureFlag
from lp.services.fields import UniqueField
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
from lp.services.webapp.snapshot import notify_modified
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
    links = [
        "edit",
        "reviewer",
        "permissions",
        "activity",
        "webhooks",
        "delete",
        ]

    @enabled_with_permission("launchpad.Edit")
    def edit(self):
        text = "Change repository details"
        return Link("+edit", text, icon="edit")

    @enabled_with_permission("launchpad.Edit")
    def reviewer(self):
        text = "Set repository reviewer"
        return Link("+reviewer", text, icon="edit")

    @enabled_with_permission("launchpad.Edit")
    def permissions(self):
        text = "Manage permissions"
        return Link("+permissions", text, icon="edit")

    @enabled_with_permission("launchpad.Edit")
    def webhooks(self):
        text = "Manage webhooks"
        return Link(
            "+webhooks", text, icon="edit",
            enabled=bool(getFeatureFlag('webhooks.new.enabled')))

    @enabled_with_permission("launchpad.Edit")
    def activity(self):
        text = "View activity"
        return Link("+activity", text, icon="info")

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
        """Return a filtered list of active landing targets."""
        targets = self.context.getPrecachedLandingTargets(
            self.user, only_active=True)
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


def encode_form_field_id(value):
    """Encode text for use in form field names.

    We use a modified version of base32 which fits into CSS identifiers and
    so doesn't cause FormattersAPI.zope_css_id to do unhelpful things.
    """
    return base64.b32encode(
        value.encode("UTF-8")).decode("UTF-8").replace("=", "_")


def decode_form_field_id(encoded):
    """Inverse of `encode_form_field_id`."""
    return base64.b32decode(
        encoded.replace("_", "=").encode("UTF-8")).decode("UTF-8")


class GitRulePatternField(UniqueField):

    errormessage = _("%s is already in use by another rule")
    attribute = "ref_pattern"
    _content_iface = IGitRepository

    def __init__(self, ref_prefix, rule=None, *args, **kwargs):
        self.ref_prefix = ref_prefix
        self.rule = rule
        super(GitRulePatternField, self).__init__(*args, **kwargs)

    def _getByAttribute(self, ref_pattern):
        """See `UniqueField`."""
        if self._content_iface.providedBy(self.context):
            return self.context.getRule(self.ref_prefix + ref_pattern)
        else:
            return None

    def unchanged(self, input):
        """See `UniqueField`."""
        return (
            self.rule is not None and
            self.ref_prefix + input == self.rule.ref_pattern)

    def set(self, object, value):
        """See `IField`."""
        if value is not None:
            value = value.strip()
        super(GitRulePatternField, self).set(object, value)


class GitRepositoryPermissionsView(LaunchpadFormView):
    """A view to manage repository permissions."""

    @property
    def label(self):
        return "Manage permissions for %s" % self.context.identity

    page_title = "Manage permissions"

    @cachedproperty
    def repository(self):
        return self.context

    @cachedproperty
    def rules(self):
        return self.repository.getRules()

    @cachedproperty
    def branch_rules(self):
        return [
            rule for rule in self.rules
            if rule.ref_pattern.startswith(u"refs/heads/")]

    @cachedproperty
    def tag_rules(self):
        return [
            rule for rule in self.rules
            if rule.ref_pattern.startswith(u"refs/tags/")]

    @cachedproperty
    def other_rules(self):
        return [
            rule for rule in self.rules
            if not rule.ref_pattern.startswith(u"refs/heads/") and
               not rule.ref_pattern.startswith(u"refs/tags/")]

    def _getRuleGrants(self, rule):
        def grantee_key(grant):
            if grant.grantee is not None:
                return grant.grantee_type, grant.grantee.name
            else:
                return (grant.grantee_type,)

        return sorted(rule.grants, key=grantee_key)

    def _parseRefPattern(self, ref_pattern):
        """Parse a pattern into a prefix and the displayed portion."""
        for prefix in (u"refs/heads/", u"refs/tags/"):
            if ref_pattern.startswith(prefix):
                return prefix, ref_pattern[len(prefix):]
        return u"", ref_pattern

    def _getFieldName(self, name, ref_pattern, grantee=None):
        """Get the combined field name for a ref pattern and optional grantee.

        In order to be able to render a permissions table, we encode the ref
        pattern and the grantee in the form field name.
        """
        suffix = "." + encode_form_field_id(ref_pattern)
        if grantee is not None:
            if IPerson.providedBy(grantee):
                suffix += "." + str(grantee.id)
            else:
                suffix += "._" + grantee.name.lower()
        return name + suffix

    def _parseFieldName(self, field_name):
        """Parse a combined field name as described in `_getFieldName`.

        :raises UnexpectedFormData: if the field name cannot be parsed or
            the grantee cannot be found.
        """
        field_bits = field_name.split(".")
        if len(field_bits) < 2:
            raise UnexpectedFormData(
                "Cannot parse field name: %s" % field_name)
        field_type = field_bits[0]
        try:
            ref_pattern = decode_form_field_id(field_bits[1])
        except TypeError:
            raise UnexpectedFormData(
                "Cannot parse field name: %s" % field_name)
        if len(field_bits) > 2:
            grantee_id = field_bits[2]
            if grantee_id.startswith("_"):
                grantee_id = grantee_id[1:]
                try:
                    grantee = GitGranteeType.getTermByToken(grantee_id).value
                except LookupError:
                    grantee = None
            else:
                try:
                    grantee_id = int(grantee_id)
                except ValueError:
                    grantee = None
                else:
                    grantee = getUtility(IPersonSet).get(grantee_id)
            if grantee is None or grantee == GitGranteeType.PERSON:
                raise UnexpectedFormData("No such grantee: %s" % grantee_id)
        else:
            grantee = None
        return field_type, ref_pattern, grantee

    def _getPermissionsTerm(self, grant):
        """Return a term from `GitPermissionsVocabulary` for this grant."""
        vocabulary = getVocabularyRegistry().get(grant, "GitPermissions")
        try:
            return vocabulary.getTerm(grant.permissions)
        except LookupError:
            # This should never happen, because GitPermissionsVocabulary
            # adds a custom term for the context grant if necessary.
            raise AssertionError(
                "Could not find GitPermissions term for %r" % grant)

    def setUpFields(self):
        """See `LaunchpadFormView`."""
        position_fields = []
        pattern_fields = []
        delete_fields = []
        readonly_grantee_fields = []
        grantee_fields = []
        permissions_fields = []

        default_permissions_by_prefix = {
            "refs/heads/": "can_push",
            "refs/tags/": "can_create",
            "": "can_push",
            }

        for rule_index, rule in enumerate(self.rules):
            # Remove the usual branch/tag prefixes from patterns.  The full
            # pattern goes into form field names, so no data is lost here.
            ref_pattern = rule.ref_pattern
            ref_prefix, short_pattern = self._parseRefPattern(ref_pattern)
            position_fields.append(
                Int(
                    __name__=self._getFieldName("position", ref_pattern),
                    required=True, readonly=False, default=rule_index + 1))
            pattern_fields.append(
                GitRulePatternField(
                    __name__=self._getFieldName("pattern", ref_pattern),
                    required=True, readonly=False, ref_prefix=ref_prefix,
                    rule=rule, default=short_pattern))
            delete_fields.append(
                Bool(
                    __name__=self._getFieldName("delete", ref_pattern),
                    readonly=False, default=False))
            for grant in self._getRuleGrants(rule):
                grantee = grant.combined_grantee
                readonly_grantee_fields.append(
                    GitGranteeField(
                        __name__=self._getFieldName(
                            "grantee", ref_pattern, grantee),
                        required=False, readonly=True, default=grantee,
                        rule=rule))
                permissions_fields.append(
                    Choice(
                        __name__=self._getFieldName(
                            "permissions", ref_pattern, grantee),
                        source=GitPermissionsVocabulary(grant),
                        readonly=False,
                        default=self._getPermissionsTerm(grant).value))
                delete_fields.append(
                    Bool(
                        __name__=self._getFieldName(
                            "delete", ref_pattern, grantee),
                        readonly=False, default=False))
            grantee_fields.append(
                GitGranteeField(
                    __name__=self._getFieldName("grantee", ref_pattern),
                    required=False, readonly=False, rule=rule))
            permissions_vocabulary = GitPermissionsVocabulary(rule)
            permissions_fields.append(
                Choice(
                    __name__=self._getFieldName(
                        "permissions", ref_pattern),
                    source=permissions_vocabulary, readonly=False,
                    default=permissions_vocabulary.getTermByToken(
                        default_permissions_by_prefix[ref_prefix]).value))
        for ref_prefix in ("refs/heads/", "refs/tags/"):
            position_fields.append(
                Int(
                    __name__=self._getFieldName("new-position", ref_prefix),
                    required=False, readonly=True))
            pattern_fields.append(
                GitRulePatternField(
                    __name__=self._getFieldName("new-pattern", ref_prefix),
                    required=False, readonly=False, ref_prefix=ref_prefix))

        self.form_fields = (
            form.FormFields(
                *position_fields,
                custom_widget=CustomWidgetFactory(IntWidget, displayWidth=2)) +
            form.FormFields(*pattern_fields) +
            form.FormFields(*delete_fields) +
            form.FormFields(
                *readonly_grantee_fields,
                custom_widget=CustomWidgetFactory(GitGranteeDisplayWidget)) +
            form.FormFields(
                *grantee_fields,
                custom_widget=CustomWidgetFactory(GitGranteeWidget)) +
            form.FormFields(*permissions_fields))

    def setUpWidgets(self, context=None):
        """See `LaunchpadFormView`."""
        super(GitRepositoryPermissionsView, self).setUpWidgets(
            context=context)
        for widget in self.widgets:
            widget.display_label = False
            widget.hint = None

    @property
    def cancel_url(self):
        return canonical_url(self.context)

    def getRuleWidgets(self, rule):
        widgets_by_name = {widget.name: widget for widget in self.widgets}
        ref_pattern = rule.ref_pattern
        position_field_name = (
            "field." + self._getFieldName("position", ref_pattern))
        pattern_field_name = (
            "field." + self._getFieldName("pattern", ref_pattern))
        delete_field_name = (
            "field." + self._getFieldName("delete", ref_pattern))
        grant_widgets = []
        for grant in self._getRuleGrants(rule):
            grantee = grant.combined_grantee
            grantee_field_name = (
                "field." + self._getFieldName("grantee", ref_pattern, grantee))
            permissions_field_name = (
                "field." +
                self._getFieldName("permissions", ref_pattern, grantee))
            delete_grant_field_name = (
                "field." + self._getFieldName("delete", ref_pattern, grantee))
            grant_widgets.append({
                "grantee": widgets_by_name[grantee_field_name],
                "permissions": widgets_by_name[permissions_field_name],
                "delete": widgets_by_name[delete_grant_field_name],
                })
        new_grantee_field_name = (
            "field." + self._getFieldName("grantee", ref_pattern))
        new_permissions_field_name = (
            "field." + self._getFieldName("permissions", ref_pattern))
        new_grant_widgets = {
            "grantee": widgets_by_name[new_grantee_field_name],
            "permissions": widgets_by_name[new_permissions_field_name],
            }
        return {
            "position": widgets_by_name[position_field_name],
            "pattern": widgets_by_name[pattern_field_name],
            "delete": widgets_by_name.get(delete_field_name),
            "grants": grant_widgets,
            "new_grant": new_grant_widgets,
            }

    def getNewRuleWidgets(self, ref_prefix):
        widgets_by_name = {widget.name: widget for widget in self.widgets}
        new_position_field_name = (
            "field." + self._getFieldName("new-position", ref_prefix))
        new_pattern_field_name = (
            "field." + self._getFieldName("new-pattern", ref_prefix))
        return {
            "position": widgets_by_name[new_position_field_name],
            "pattern": widgets_by_name[new_pattern_field_name],
            }

    def updateRepositoryFromData(self, repository, data):
        pattern_field_names = sorted(
            name for name in data if name.split(".")[0] == "pattern")
        new_pattern_field_names = sorted(
            name for name in data if name.split(".")[0] == "new-pattern")
        permissions_field_names = sorted(
            name for name in data if name.split(".")[0] == "permissions")

        # Fetch rules before making any changes, since their ref_patterns
        # may change as a result of this update.
        rule_map = {rule.ref_pattern: rule for rule in self.repository.rules}
        grant_map = {
            (grant.rule.ref_pattern, grant.combined_grantee): grant
            for grant in self.repository.grants}

        # Patterns must be processed in rule order so that position changes
        # work in a reasonably natural way.
        ordered_patterns = []
        for pattern_field_name in pattern_field_names:
            _, ref_pattern, _ = self._parseFieldName(pattern_field_name)
            if ref_pattern is not None:
                rule = rule_map.get(ref_pattern)
                ordered_patterns.append(
                    (pattern_field_name, ref_pattern, rule))
        ordered_patterns.sort(key=lambda item: item[2].position)

        for pattern_field_name, ref_pattern, rule in ordered_patterns:
            prefix, _ = self._parseRefPattern(ref_pattern)
            rule = rule_map.get(ref_pattern)
            delete_field_name = self._getFieldName("delete", ref_pattern)
            # If the rule was already deleted by somebody else, then we
            # have nothing to do.
            if rule is not None and data.get(delete_field_name):
                rule.destroySelf(self.user)
                rule_map[ref_pattern] = rule = None
            position_field_name = self._getFieldName("position", ref_pattern)
            if rule is not None:
                new_position = max(0, data[position_field_name] - 1)
                self.repository.moveRule(rule, new_position, self.user)
            new_pattern = prefix + data[pattern_field_name]
            if rule is not None and new_pattern != rule.ref_pattern:
                with notify_modified(rule, ["ref_pattern"]):
                    rule.ref_pattern = new_pattern

        for new_pattern_field_name in new_pattern_field_names:
            _, prefix, _ = self._parseFieldName(new_pattern_field_name)
            if data[new_pattern_field_name]:
                # This is an "add rule" entry.
                new_position_field_name = self._getFieldName(
                    "position", prefix)
                new_pattern = prefix + data[new_pattern_field_name]
                rule = rule_map.get(new_pattern)
                if rule is None:
                    if new_position_field_name in data:
                        new_position = max(
                            0, data[new_position_field_name] - 1)
                    else:
                        new_position = None
                    rule = repository.addRule(
                        new_pattern, self.user, position=new_position)
                    if prefix == "refs/tags/":
                        # Tags are a special case: on creation, they
                        # automatically get a grant of create permissions to
                        # the repository owner (suppressing the normal
                        # ability of the repository owner to push protected
                        # references).
                        rule.addGrant(
                            GitGranteeType.REPOSITORY_OWNER, self.user,
                            can_create=True)

        for permissions_field_name in permissions_field_names:
            _, ref_pattern, grantee = self._parseFieldName(
                permissions_field_name)
            if ref_pattern not in rule_map:
                self.addError(structured(
                    "Cannot edit grants for nonexistent rule %s", ref_pattern))
                return
            rule = rule_map.get(ref_pattern)
            if rule is None:
                # Already deleted.
                continue

            # Find or create the corresponding grant.  We only create a
            # grant if explicitly processing an "add grant" entry in the UI;
            # if there isn't already a grant for an existing entry that's
            # being modified, implicitly adding it is probably too
            # confusing.
            permissions = data[permissions_field_name]
            grant = None
            if grantee is not None:
                # This entry should correspond to an existing grant.  Make
                # whatever changes were requested to it.
                grant = grant_map.get((ref_pattern, grantee))
                delete_field_name = self._getFieldName(
                    "delete", ref_pattern, grantee)
                # If the grant was already deleted by somebody else, then we
                # have nothing to do.
                if grant is not None and data.get(delete_field_name):
                    grant.destroySelf(self.user)
                    grant = None
                if grant is not None and permissions != grant.permissions:
                    with notify_modified(
                            grant,
                            ["can_create", "can_push", "can_force_push"]):
                        grant.permissions = permissions
            else:
                # This is an "add grant" entry.
                grantee_field_name = self._getFieldName("grantee", ref_pattern)
                grantee = data.get(grantee_field_name)
                if grantee:
                    grant = grant_map.get((ref_pattern, grantee))
                    if grant is None:
                        rule.addGrant(
                            grantee, self.user, permissions=permissions)
                    elif permissions != grant.permissions:
                        # Somebody else added the grant since the form was
                        # last rendered.  Updating it with the permissions
                        # from this request seems best.
                        with notify_modified(
                                grant,
                                ["can_create", "can_push", "can_force_push"]):
                            grant.permissions = permissions

        self.request.response.addNotification(
            "Saved permissions for %s" % self.context.identity)
        self.next_url = canonical_url(self.context, view_name="+permissions")

    @action("Save", name="save")
    def save_action(self, action, data):
        with notify_modified(self.repository, []):
            self.updateRepositoryFromData(self.repository, data)


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


class GitRepositoryActivityView(LaunchpadView):

    page_title = "Activity"

    @property
    def label(self):
        return "Activity log for %s" % self.context.display_name

    def displayPermissions(self, values):
        """Assemble a human readable list from the permissions changes."""
        permissions = []
        if values.get('can_create'):
            permissions.append('create')
        if values.get('can_push'):
            permissions.append('push')
        if values.get('can_force_push'):
            permissions.append('force-push')
        return ', '.join(permissions)
