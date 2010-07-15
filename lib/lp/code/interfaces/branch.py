# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213,F0401,W0611

"""Branch interfaces."""

__metaclass__ = type

__all__ = [
    'BRANCH_NAME_VALIDATION_ERROR_MESSAGE',
    'branch_name_validator',
    'BranchCannotBePrivate',
    'BranchCannotBePublic',
    'BranchCreationException',
    'BranchCreationForbidden',
    'BranchCreationNoTeamOwnedJunkBranches',
    'BranchCreatorNotMemberOfOwnerTeam',
    'BranchCreatorNotOwner',
    'BranchExists',
    'BranchTargetError',
    'BranchTypeError',
    'BzrIdentityMixin',
    'CannotDeleteBranch',
    'DEFAULT_BRANCH_STATUS_IN_LISTING',
    'get_blacklisted_hostnames',
    'IBranch',
    'IBranchBatchNavigator',
    'IBranchCloud',
    'IBranchDelta',
    'IBranchListingQueryOptimiser',
    'IBranchNavigationMenu',
    'IBranchSet',
    'NoSuchBranch',
    'user_has_special_branch_access',
    ]

from cgi import escape
import re

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Int, Choice, List, Text, TextLine, Datetime)

from lazr.restful.fields import CollectionField, Reference, ReferenceChoice
from lazr.restful.declarations import (
    REQUEST_USER, call_with, collection_default_content,
    export_as_webservice_collection, export_as_webservice_entry,
    export_destructor_operation, export_factory_operation,
    export_operation_as, export_read_operation, export_write_operation,
    exported, mutator_for, operation_parameters, operation_returns_entry,
    webservice_error)

from canonical.config import config

from canonical.launchpad import _
from canonical.launchpad.fields import (
    ParticipatingPersonChoice, PublicPersonChoice, URIField, Whiteboard)
from canonical.launchpad.validators import LaunchpadValidationError
from lp.code.bzr import BranchFormat, ControlFormat, RepositoryFormat
from lp.code.enums import (
    BranchLifecycleStatus,
    BranchMergeControlStatus,
    BranchSubscriptionNotificationLevel, BranchSubscriptionDiffSize,
    CodeReviewNotificationLevel,
    UICreatableBranchType,
    )
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.code.interfaces.branchtarget import IHasBranchTarget
from lp.code.interfaces.linkedbranch import ICanHasLinkedBranch
from lp.code.interfaces.hasbranches import IHasMergeProposals
from lp.code.interfaces.hasrecipes import IHasRecipes
from canonical.launchpad.interfaces.launchpad import (
    ILaunchpadCelebrities, IPrivacy)
from lp.registry.interfaces.role import IHasOwner
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.pocket import PackagePublishingPocket
from canonical.launchpad.webapp.interfaces import (
    ITableBatchNavigator, NameLookupFailed)
from canonical.launchpad.webapp.menu import structured


DEFAULT_BRANCH_STATUS_IN_LISTING = (
    BranchLifecycleStatus.EXPERIMENTAL,
    BranchLifecycleStatus.DEVELOPMENT,
    BranchLifecycleStatus.MATURE)


class BranchCreationException(Exception):
    """Base class for branch creation exceptions."""


class BranchExists(BranchCreationException):
    """Raised when creating a branch that already exists."""

    webservice_error(400)

    def __init__(self, existing_branch):
        # XXX: TimPenhey 2009-07-12 bug=405214: This error
        # message logic is incorrect, but the exact text is being tested
        # in branch-xmlrpc.txt.
        params = {'name': existing_branch.name}
        if existing_branch.product is None:
            params['maybe_junk'] = 'junk '
            params['context'] = existing_branch.owner.name
        else:
            params['maybe_junk'] = ''
            params['context'] = '%s in %s' % (
                existing_branch.owner.name, existing_branch.product.name)
        message = (
            'A %(maybe_junk)sbranch with the name "%(name)s" already exists '
            'for %(context)s.' % params)
        self.existing_branch = existing_branch
        BranchCreationException.__init__(self, message)


class BranchTargetError(Exception):
    """Raised when there is an error determining a branch target."""


class CannotDeleteBranch(Exception):
    """The branch cannot be deleted at this time."""


class BranchCreationForbidden(BranchCreationException):
    """A Branch visibility policy forbids branch creation.

    The exception is raised if the policy for the product does not allow
    the creator of the branch to create a branch for that product.
    """


class BranchCreatorNotMemberOfOwnerTeam(BranchCreationException):
    """Branch creator is not a member of the owner team.

    Raised when a user is attempting to create a branch and set the owner of
    the branch to a team that they are not a member of.
    """

    webservice_error(400)


class BranchCreationNoTeamOwnedJunkBranches(BranchCreationException):
    """We forbid the creation of team-owned +junk branches.

    Raised when a user is attempting to create a team-owned +junk branch.
    """

    error_message = (
        "+junk branches are only available for individuals. Please consider "
        "registering a project for collaborating on branches: "
        "https://help.launchpad.net/Projects/Registering")

    def __init__(self):
        BranchCreationException.__init__(self, self.error_message)


class BranchCreatorNotOwner(BranchCreationException):
    """A user cannot create a branch belonging to another user.

    Raised when a user is attempting to create a branch and set the owner of
    the branch to another user.
    """

    webservice_error(400)


class BranchTypeError(Exception):
    """An operation cannot be performed for a particular branch type.

    Some branch operations are only valid for certain types of branches.  The
    BranchTypeError exception is raised if one of these operations is called
    with a branch of the wrong type.
    """


class BranchCannotBePublic(Exception):
    """The branch cannot be made public."""


class BranchCannotBePrivate(Exception):
    """The branch cannot be made private."""


class NoSuchBranch(NameLookupFailed):
    """Raised when we try to load a branch that does not exist."""

    _message_prefix = "No such branch"


def get_blacklisted_hostnames():
    """Return a list of hostnames blacklisted for Branch URLs."""
    hostnames = config.codehosting.blacklisted_hostnames
    # If nothing specified, return an empty list. Special-casing since
    # ''.split(',') == [''].
    if hostnames == '':
        return []
    return hostnames.split(',')


class BranchURIField(URIField):

    #XXX leonardr 2009-02-12 [bug=328588]:
    # This code should be removed once the underlying database restriction
    # is removed.
    trailing_slash = False

    # XXX leonardr 2009-02-12 [bug=328588]:
    # This code should be removed once the underlying database restriction
    # is removed.
    def normalize(self, input):
        """Be extra-strict about trailing slashes."""
        # Can't use super-- this derives from an old-style class
        input = URIField.normalize(self, input)
        if self.trailing_slash == False and input[-1] == '/':
            # ensureNoSlash() doesn't trim the slash if the path
            # is empty (eg. http://example.com/). Due to the database
            # restriction on branch URIs, we need to remove a trailing
            # slash in all circumstances.
            input = input[:-1]
        return input

    def _validate(self, value):
        # import here to avoid circular import
        from canonical.launchpad.webapp import canonical_url
        from lazr.uri import URI

        # Can't use super-- this derives from an old-style class
        URIField._validate(self, value)

        # XXX thumper 2007-06-12:
        # Move this validation code into IBranchSet so it can be
        # reused in the XMLRPC code, and the Authserver.
        # This also means we could get rid of the imports above.

        uri = URI(self.normalize(value))
        launchpad_domain = config.vhost.mainsite.hostname
        if uri.underDomain(launchpad_domain):
            message = _(
                "For Launchpad to mirror a branch, the original branch "
                "cannot be on <code>${domain}</code>.",
                mapping={'domain': escape(launchpad_domain)})
            raise LaunchpadValidationError(structured(message))

        for hostname in get_blacklisted_hostnames():
            if uri.underDomain(hostname):
                message = _(
                    'Launchpad cannot mirror branches from %s.' % hostname)
                raise LaunchpadValidationError(structured(message))

        # As well as the check against the config, we also need to check
        # against the actual text used in the database constraint.
        constraint_text = 'http://bazaar.launchpad.net'
        if value.startswith(constraint_text):
            message = _(
                "For Launchpad to mirror a branch, the original branch "
                "cannot be on <code>${domain}</code>.",
                mapping={'domain': escape(constraint_text)})
            raise LaunchpadValidationError(structured(message))

        if IBranch.providedBy(self.context) and self.context.url == str(uri):
            return # url was not changed

        if uri.path == '/':
            message = _(
                "URLs for branches cannot point to the root of a site.")
            raise LaunchpadValidationError(message)

        branch = getUtility(IBranchLookup).getByUrl(str(uri))
        if branch is not None:
            message = _(
                'The bzr branch <a href="${url}">${branch}</a> is '
                'already registered with this URL.',
                mapping={'url': canonical_url(branch),
                         'branch': escape(branch.displayname)})
            raise LaunchpadValidationError(structured(message))


BRANCH_NAME_VALIDATION_ERROR_MESSAGE = _(
    "Branch names must start with a number or letter.  The characters +, -, "
    "_, . and @ are also allowed after the first character.")


# This is a copy of the pattern in database/schema/trusted.sql.  Don't
# change this without changing that.
valid_branch_name_pattern = re.compile(r"^(?i)[a-z0-9][a-z0-9+\.\-@_]*\Z")


def valid_branch_name(name):
    """Return True if the name is valid as a branch name, otherwise False.

    The rules for what is a valid branch name are described in
    BRANCH_NAME_VALIDATION_ERROR_MESSAGE.
    """
    if valid_branch_name_pattern.match(name):
        return True
    return False


def branch_name_validator(name):
    """Return True if the name is valid, or raise a LaunchpadValidationError.
    """
    if not valid_branch_name(name):
        raise LaunchpadValidationError(
            _("Invalid branch name '${name}'. ${message}",
              mapping={'name': name,
                       'message': BRANCH_NAME_VALIDATION_ERROR_MESSAGE}))
    return True


class IBranchBatchNavigator(ITableBatchNavigator):
    """A marker interface for registering the appropriate branch listings."""


class IBranchNavigationMenu(Interface):
    """A marker interface to indicate the need to show the branch menu."""


class IBranch(IHasOwner, IPrivacy, IHasBranchTarget, IHasMergeProposals,
              IHasRecipes):
    """A Bazaar branch."""

    # Mark branches as exported entries for the Launchpad API.
    export_as_webservice_entry(plural_name='branches')

    id = Int(title=_('ID'), readonly=True, required=True)

    # XXX: TimPenhey 2007-08-31
    # The vocabulary set for branch_type is only used for the creation
    # of branches through the automatically generated forms, and doesn't
    # actually represent the complete range of real values that branch_type
    # may actually hold.  Import branches are not created in the same
    # way as Hosted, Mirrored or Remote branches.
    # There are two option:
    #   1) define a separate schema to use in the UI (sledgehammer solution)
    #   2) work out some way to specify a restricted vocabulary in the view
    # Personally I'd like a LAZR way to do number 2.
    branch_type = exported(
        Choice(
            title=_("Branch Type"), required=True, readonly=True,
            vocabulary=UICreatableBranchType))

    name = exported(
        TextLine(
            title=_('Name'), required=True, constraint=branch_name_validator,
            description=_(
                "Keep very short, unique, and descriptive, because it will "
                "be used in URLs.  "
                "Examples: main, devel, release-1.0, gnome-vfs.")))

    url = exported(
        BranchURIField(
            title=_('Branch URL'), required=False,
            allowed_schemes=['http', 'https', 'ftp', 'sftp', 'bzr+ssh'],
            allow_userinfo=False,
            allow_query=False,
            allow_fragment=False,
            trailing_slash=False,
            description=_(
                "This is the external location where the Bazaar "
                "branch is hosted.")))

    @operation_parameters(
        scheme=TextLine(title=_("URL scheme"), default=u'http'))
    @export_read_operation()
    def composePublicURL(scheme='http'):
        """Return a public URL for the branch using the given protocol.

        :param scheme: a protocol name accepted by the public
            code-hosting API.  (As a legacy issue, 'sftp' is also
            accepted).
        """

    description = exported(
        Text(
            title=_('Description'), required=False,
            description=_(
                'A short description of the changes in this branch.')))

    branch_format = exported(
        Choice(
            title=_("Branch Format"),
            required=False, readonly=True,
            vocabulary=BranchFormat))

    repository_format = exported(
        Choice(
            title=_("Repository Format"),
            required=False, readonly=True,
            vocabulary=RepositoryFormat))

    control_format = exported(
        Choice(
            title=_("Control Directory"),
            required=False, readonly=True,
            vocabulary=ControlFormat))

    whiteboard = exported(
        Whiteboard(
            title=_('Whiteboard'), required=False,
            description=_('Notes on the current status of the branch.')))

    mirror_status_message = exported(
        Text(
            title=_('The last message we got when mirroring this branch.'),
            required=False, readonly=True))

    # This is redefined from IPrivacy.private because the attribute is
    # read-only. The value is guarded by setPrivate().
    private = exported(
        Bool(
            title=_("Keep branch confidential"), required=False,
            readonly=True, default=False,
            description=_(
                "Make this branch visible only to its subscribers.")))

    @mutator_for(private)
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        private=Bool(title=_("Keep branch confidential")))
    @export_write_operation()
    def setPrivate(private, user):
        """Set the branch privacy for this branch."""

    # People attributes
    registrant = exported(
        PublicPersonChoice(
            title=_("The user that registered the branch."),
            required=True, readonly=True,
            vocabulary='ValidPersonOrTeam'))

    owner = exported(
        ParticipatingPersonChoice(
            title=_('Owner'),
            required=True, readonly=True,
            vocabulary='UserTeamsParticipationPlusSelf',
            description=_("Either yourself or a team you are a member of. "
                          "This controls who can modify the branch.")))

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        new_owner=Reference(
            title=_("The new owner of the branch."),
            schema=IPerson))
    @export_write_operation()
    def setOwner(new_owner, user):
        """Set the owner of the branch to be `new_owner`."""

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        project=Reference(
            title=_("The project the branch belongs to."),
            schema=Interface, required=False), # Really IProduct
        source_package=Reference(
            title=_("The source package the branch belongs to."),
            schema=Interface, required=False)) # Really ISourcePackage
    @export_write_operation()
    def setTarget(user, project=None, source_package=None):
        """Set the target of the branch to be `project` or `source_package`.

        Only one of `project` or `source_package` can be set, and if neither
        is set, the branch gets moved into the junk namespace of the branch
        owner.

        :raise: `BranchTargetError` if both project and source_package are set,
          or if either the project or source_package fail to be adapted to an
          IBranchTarget.
        """

    reviewer = exported(
        PublicPersonChoice(
            title=_('Review Team'),
            required=False,
            vocabulary='ValidPersonOrTeam',
            description=_("The reviewer of a branch is the person or team "
                          "that is responsible for reviewing proposals and "
                          "merging into this branch.")))

    # Distroseries and sourcepackagename are exported together as
    # the sourcepackage.
    distroseries = Choice(
        title=_("Distribution Series"), required=False,
        vocabulary='DistroSeries',
        description=_(
            "The distribution series that this branch belongs to. Branches "
            "do not have to belong to a distribution series, they can also "
            "belong to a project or be junk branches."))

    sourcepackagename = Choice(
        title=_("Source Package Name"), required=True,
        vocabulary='SourcePackageName',
        description=_(
            "The source package that this is a branch of. Source package "
            "branches always belong to a distribution series."))

    distribution = Attribute(
        "The IDistribution that this branch belongs to. None if not a "
        "package branch.")

    # Really an ISourcePackage.
    sourcepackage = exported(
        Reference(
            title=_("The ISourcePackage that this branch belongs to. "
                    "None if not a package branch."),
            schema=Interface, required=False, readonly=True))

    code_reviewer = Attribute(
        "The reviewer if set, otherwise the owner of the branch.")

    @operation_parameters(
        reviewer=Reference(
            title=_("A person for which the reviewer status is in question."),
            schema=IPerson))
    @export_read_operation()
    def isPersonTrustedReviewer(reviewer):
        """Return true if the `reviewer` is a trusted reviewer.

        The reviewer is trusted if they are either own the branch, or are in
        the team that owns the branch, or they are in the review team for the
        branch.
        """

    namespace = Attribute(
        "The namespace of this branch, as an `IBranchNamespace`.")

    # Product attributes
    # ReferenceChoice is Interface rather than IProduct as IProduct imports
    # IBranch and we'd get import errors.  IPerson does a similar trick.
    # The schema is set properly to `IProduct` in _schema_circular_imports.
    product = exported(
        ReferenceChoice(
            title=_('Project'),
            required=False, readonly=True,
            vocabulary='Product',
            schema=Interface,
            description=_("The project this branch belongs to.")),
        exported_as='project')

    # Display attributes
    unique_name = exported(
        Text(title=_('Unique name'), readonly=True,
             description=_("Unique name of the branch, including the "
                           "owner and project names.")))

    displayname = exported(
        Text(title=_('Display name'), readonly=True,
             description=_(
                "The branch unique_name.")),
        exported_as='display_name')

    # Stats and status attributes
    lifecycle_status = exported(
        Choice(
            title=_('Status'), vocabulary=BranchLifecycleStatus,
            default=BranchLifecycleStatus.DEVELOPMENT))

    # Mirroring attributes. For more information about how these all relate to
    # each other, look at
    # 'lib/canonical/launchpad/doc/puller-state-table.ods'.
    last_mirrored = exported(
        Datetime(
            title=_("Last time this branch was successfully mirrored."),
            required=False, readonly=True))
    last_mirrored_id = Text(
        title=_("Last mirrored revision ID"), required=False,
        description=_("The head revision ID of the branch when last "
                      "successfully mirrored."))
    last_mirror_attempt = exported(
        Datetime(
            title=_("Last time a mirror of this branch was attempted."),
            required=False, readonly=True))
    mirror_failures = Attribute(
        "Number of failed mirror attempts since the last successful mirror.")
    next_mirror_time = Datetime(
        title=_("If this value is more recent than the last mirror attempt, "
                "then the branch will be mirrored on the next mirror run."),
        required=False)

    # Scanning attributes
    last_scanned = exported(
        Datetime(
            title=_("Last time this branch was successfully scanned."),
            required=False, readonly=True))
    last_scanned_id = exported(
        TextLine(
            title=_("Last scanned revision ID"),
            required=False, readonly=True,
            description=_("The head revision ID of the branch when last "
                          "successfully scanned.")))

    revision_count = exported(
        Int(
            title=_("Revision count"), readonly=True,
            description=_("The revision number of the tip of the branch.")))

    stacked_on = Attribute('Stacked-on branch')

    # Bug attributes
    bug_branches = CollectionField(
            title=_("The bug-branch link objects that link this branch "
                    "to bugs."),
            readonly=True,
            value_type=Reference(schema=Interface)) # Really IBugBranch

    linked_bugs = exported(
        CollectionField(
            title=_("The bugs linked to this branch."),
        readonly=True,
        value_type=Reference(schema=Interface))) # Really IBug

    def getLinkedBugsAndTasks():
        """Return a result set for the bugs with their tasks."""

    @call_with(registrant=REQUEST_USER)
    @operation_parameters(
        bug=Reference(schema=Interface)) # Really IBug
    @export_write_operation()
    def linkBug(bug, registrant):
        """Link a bug to this branch.

        :param bug: IBug to link.
        :param registrant: IPerson linking the bug.
        """

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        bug=Reference(schema=Interface)) # Really IBug
    @export_write_operation()
    def unlinkBug(bug, user):
        """Unlink a bug to this branch.

        :param bug: IBug to unlink.
        :param user: IPerson unlinking the bug.
        """

    # Specification attributes
    spec_links = exported(
        CollectionField(
            title=_("Specification linked to this branch."),
            readonly=True,
            value_type=Reference(Interface))) # Really ISpecificationBranch

    @call_with(registrant=REQUEST_USER)
    @operation_parameters(
        spec=Reference(schema=Interface)) # Really ISpecification
    @export_write_operation()
    def linkSpecification(spec, registrant):
        """Link an ISpecification to a branch.

        :param spec: ISpecification to link.
        :param registrant: IPerson unlinking the spec.
        """

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        spec=Reference(schema=Interface)) # Really ISpecification
    @export_write_operation()
    def unlinkSpecification(spec, user):
        """Unlink an ISpecification to a branch.

        :param spec: ISpecification to unlink.
        :param user: IPerson unlinking the spec.
        """

    pending_writes = Attribute(
        "Whether there is new Bazaar data for this branch.")

    # Joins
    revision_history = Attribute(
        """The sequence of BranchRevision for the mainline of that branch.

        They are ordered with the most recent revision first, and the list
        only contains those in the "leftmost tree", or in other words
        the revisions that match the revision history from bzrlib for this
        branch.
        """)
    subscriptions = exported(
        CollectionField(
            title=_("BranchSubscriptions associated to this branch."),
            readonly=True,
            value_type=Reference(Interface))) # Really IBranchSubscription

    subscribers = exported(
        CollectionField(
            title=_("Persons subscribed to this branch."),
            readonly=True,
            value_type=Reference(IPerson)))

    date_created = exported(
        Datetime(
            title=_('Date Created'),
            required=True,
            readonly=True))

    date_last_modified = exported(
        Datetime(
            title=_('Date Last Modified'),
            required=True,
            readonly=False))

    @export_destructor_operation()
    def destroySelfBreakReferences():
        """Delete the specified branch.

        BranchRevisions associated with this branch will also be deleted as 
        well as any items with mandatory references.
        """

    def destroySelf(break_references=False):
        """Delete the specified branch.

        BranchRevisions associated with this branch will also be deleted.

        :param break_references: If supplied, break any references to this
            branch by deleting items with mandatory references and
            NULLing other references.
        :raise: CannotDeleteBranch if the branch cannot be deleted.
        """

    def latest_revisions(quantity=10):
        """A specific number of the latest revisions in that branch."""

    # These attributes actually have a value_type of IBranchMergeProposal,
    # but uses Interface to prevent circular imports, and the value_type is
    # set near IBranchMergeProposal.
    landing_targets = exported(
        CollectionField(
            title=_('Landing Targets'),
            description=_(
                'A collection of the merge proposals where this branch is '
                'the source branch.'),
            readonly=True,
            value_type=Reference(Interface)))
    landing_candidates = exported(
        CollectionField(
            title=_('Landing Candidates'),
            description=_(
                'A collection of the merge proposals where this branch is '
                'the target branch.'),
            readonly=True,
            value_type=Reference(Interface)))
    dependent_branches = exported(
        CollectionField(
            title=_('Dependent Branches'),
            description=_(
                'A collection of the merge proposals that are dependent '
                'on this branch.'),
            readonly=True,
            value_type=Reference(Interface)))

    def isBranchMergeable(other_branch):
        """Is the other branch mergeable into this branch (or vice versa)."""

    @export_operation_as('createMergeProposal')
    @operation_parameters(
        target_branch=Reference(schema=Interface),
        prerequisite_branch=Reference(schema=Interface),
        needs_review=Bool(title=_('Needs review'),
            description=_('If True the proposal needs review.'
            'Otherwise, it will be work in progress.')),
        initial_comment=Text(
            title=_('Initial comment'),
            description=_("Registrant's initial description of proposal.")),
        commit_message=Text(
            title=_('Commit message'),
            description=_('Message to use when committing this merge.')),
        reviewers=List(value_type=Reference(schema=IPerson)),
        review_types=List(value_type=TextLine())
        )
    # target_branch and prerequisite_branch are actually IBranch, patched in
    # _schema_circular_imports.
    @call_with(registrant=REQUEST_USER)
    # IBranchMergeProposal supplied as Interface to avoid circular imports.
    @export_factory_operation(Interface, [])
    def _createMergeProposal(
        registrant, target_branch, prerequisite_branch=None,
        needs_review=True, initial_comment=None, commit_message=None,
        reviewers=None, review_types=None):
        """Create a new BranchMergeProposal with this branch as the source.

        Both the target_branch and the prerequisite_branch, if it is there,
        must be branches with the same target as the source branch.

        Personal branches (a.k.a. junk branches) cannot specify landing targets.
        """

    def addLandingTarget(registrant, target_branch, prerequisite_branch=None,
                         date_created=None, needs_review=False,
                         description=None, review_requests=None,
                         review_diff=None, commit_message=None):
        """Create a new BranchMergeProposal with this branch as the source.

        Both the target_branch and the prerequisite_branch, if it is there,
        must be branches with the same target as the source branch.

        Personal branches (a.k.a. junk branches) cannot specify landing targets.

        :param registrant: The person who is adding the landing target.
        :param target_branch: Must be another branch, and different to self.
        :param prerequisite_branch: Optional but if it is not None, it must be
            another branch.
        :param date_created: Used to specify the date_created value of the
            merge request.
        :param needs_review: Used to specify the proposal is ready for
            review right now.
        :param description: A description of the bugs fixed, features added,
            or refactorings.
        :param review_requests: An optional list of (`Person`, review_type).
        """

    def scheduleDiffUpdates():
        """Create UpdatePreviewDiffJobs for this branch's targets."""

    def getStackedBranches():
        """The branches that are stacked on this one."""

    merge_queue = Attribute(
        "The queue that contains the QUEUED proposals for this branch.")

    merge_control_status = Choice(
        title=_('Merge Control Status'), required=True,
        vocabulary=BranchMergeControlStatus,
        default=BranchMergeControlStatus.NO_QUEUE)

    def getMergeQueue():
        """The proposals that are QUEUED to land on this branch."""

    def getMainlineBranchRevisions(start_date, end_date=None,
                                   oldest_first=False):
        """Return the matching mainline branch revision objects.

        :param start_date: Return revisions that were committed after the
            start_date.
        :param end_date: Return revisions that were committed before the
            end_date
        :param oldest_first: Defines the ordering of the result set.
        :returns: A resultset of tuples for
            (BranchRevision, Revision, RevisionAuthor)
        """

    def getRevisionsSince(timestamp):
        """Revisions in the history that are more recent than timestamp."""

    code_is_browseable = Attribute(
        "Is the code in this branch accessable through codebrowse?")

    def codebrowse_url(*extras):
        """Construct a URL for this branch in codebrowse.

        :param extras: Zero or more path segments that will be joined onto the
            end of the URL (with `bzrlib.urlutils.join`).
        """

    browse_source_url = Attribute(
        "The URL of the source browser for this branch.")

    # Really ICodeImport, but that would cause a circular import
    code_import = exported(
        Reference(
            title=_("The associated CodeImport, if any."), schema=Interface))

    bzr_identity = exported(
        Text(
            title=_('Bazaar Identity'),
            readonly=True,
            description=_(
                'The bzr branch path as accessed by Launchpad. If the '
                'branch is associated with a product as the primary '
                'development focus, then the result should be lp:product.  '
                'If the branch is related to a series, then '
                'lp:product/series.  Otherwise the result is '
                'lp:~user/product/branch-name.')))

    def addToLaunchBag(launchbag):
        """Add information about this branch to `launchbag'.

        Use this when traversing to this branch in the web UI.

        In particular, add information about the branch's target to the
        launchbag. If the branch has a product, add that; if it has a source
        package, add lots of information about that.

        :param launchbag: `ILaunchBag`.
        """

    @export_read_operation()
    def canBeDeleted():
        """Can this branch be deleted in its current state.

        A branch is considered deletable if it has no revisions, is not
        linked to any bugs, specs, productseries, or code imports, and
        has no subscribers.
        """

    def deletionRequirements():
        """Determine what is required to delete this branch.

        :return: a dict of {object: (operation, reason)}, where object is the
            object that must be deleted or altered, operation is either
            "delete" or "alter", and reason is a string explaining why the
            object needs to be touched.
        """

    def associatedProductSeries():
        """Return the product series that this branch is associated with.

        A branch may be associated with a product series is either a
        branch.  Also a branch can be associated with more than one product
        series as a branch.
        """

    def getProductSeriesPushingTranslations():
        """Return sequence of product series pushing translations here.

        These are any `ProductSeries` that have this branch as their
        translations_branch.  It should normally be at most one, but
        there's nothing stopping people from combining translations
        branches.
        """

    def associatedSuiteSourcePackages():
        """Return the suite source packages that this branch is linked to."""

    def branchLinks():
        """Return a sorted list of ICanHasLinkedBranch objects.

        There is one result for each related linked object that the branch is
        linked to.  For example in the case where a branch is linked to the
        development series of a project, the link objects for both the project
        and the development series are returned.

        The sorting uses the defined order of the linked objects where the
        more important links are sorted first.
        """

    def branchIdentities():
        """A list of aliases for a branch.

        Returns a list of tuples of bzr identity and context object.  There is
        at least one alias for any branch, and that is the branch itself.  For
        linked branches, the context object is the appropriate linked object.

        Where a branch is linked to a product series or a suite source
        package, the branch is available through a number of different urls.
        These urls are the aliases for the branch.

        For example, a branch linked to the development focus of the 'fooix'
        project is accessible using:
          lp:fooix - the linked object is the product fooix
          lp:fooix/trunk - the linked object is the trunk series of fooix
          lp:~owner/fooix/name - the unique name of the branch where the linked
            object is the branch itself.
        """

    # subscription-related methods
    @operation_parameters(
        person=Reference(
            title=_("The person to subscribe."),
            schema=IPerson),
        notification_level=Choice(
            title=_("The level of notification to subscribe to."),
            vocabulary=BranchSubscriptionNotificationLevel),
        max_diff_lines=Choice(
            title=_("The max number of lines for diff email."),
            vocabulary=BranchSubscriptionDiffSize),
        code_review_level=Choice(
            title=_("The level of code review notification emails."),
            vocabulary=CodeReviewNotificationLevel))
    @operation_returns_entry(Interface) # Really IBranchSubscription
    @call_with(subscribed_by=REQUEST_USER)
    @export_write_operation()
    def subscribe(person, notification_level, max_diff_lines,
                  code_review_level, subscribed_by):
        """Subscribe this person to the branch.

        :param person: The `Person` to subscribe.
        :param notification_level: The kinds of branch changes that cause
            notification.
        :param max_diff_lines: The maximum number of lines of diff that may
            appear in a notification.
        :param code_review_level: The kinds of code review activity that cause
            notification.
        :param subscribed_by: The person who is subscribing the subscriber.
            Most often the subscriber themselves.
        :return: new or existing BranchSubscription."""

    @operation_parameters(
        person=Reference(
            title=_("The person to unsubscribe"),
            schema=IPerson))
    @operation_returns_entry(Interface) # Really IBranchSubscription
    @export_read_operation()
    def getSubscription(person):
        """Return the BranchSubscription for this person."""

    def hasSubscription(person):
        """Is this person subscribed to the branch?"""

    @operation_parameters(
        person=Reference(
            title=_("The person to unsubscribe"),
            schema=IPerson))
    @call_with(unsubscribed_by=REQUEST_USER)
    @export_write_operation()
    def unsubscribe(person, unsubscribed_by):
        """Remove the person's subscription to this branch.

        :param person: The person or team to unsubscribe from the branch.
        :param unsubscribed_by: The person doing the unsubscribing.
        """

    def getSubscriptionsByLevel(notification_levels):
        """Return the subscriptions that are at the given notification levels.

        :param notification_levels: An iterable of
            `BranchSubscriptionNotificationLevel`s
        :return: An SQLObject query result.
        """

    def getBranchRevision(sequence=None, revision=None, revision_id=None):
        """Get the associated `BranchRevision`.

        One and only one parameter is to be not None.

        :param sequence: The revno of the revision in the mainline history.
        :param revision: A `Revision` object.
        :param revision_id: A revision id string.
        :return: A `BranchRevision` or None.
        """

    def createBranchRevision(sequence, revision):
        """Create a new `BranchRevision` for this branch."""

    def createBranchRevisionFromIDs(revision_id_sequence_pairs):
        """Create a batch of BranchRevision objects.

        :param revision_id_sequence_pairs: A sequence of (revision_id,
            sequence) pairs.  The revision_ids are assumed to have been
            inserted already; no checking of this is done.
        """

    def getTipRevision():
        """Return the `Revision` associated with the `last_scanned_id`.

        Will return None if last_scanned_id is None, or if the id
        is not found (as in a ghost revision).
        """

    def updateScannedDetails(db_revision, revision_count):
        """Updates attributes associated with the scanning of the branch.

        A single entry point that is called solely from the branch scanner
        script.

        :param revision: The `Revision` that is the tip, or None if empty.
        :param revision_count: The number of revisions in the history
                               (main line revisions).
        """

    def getNotificationRecipients():
        """Return a complete INotificationRecipientSet instance.

        The INotificationRecipientSet instance contains the subscribers
        and their subscriptions.
        """

    def getScannerData():
        """Retrieve the full ancestry of a branch for the branch scanner.

        The branch scanner script is the only place where we need to retrieve
        all the BranchRevision rows for a branch. Since the ancestry of some
        branches is into the tens of thousands we don't want to materialise
        BranchRevision instances for each of these.

        :return: tuple of three items.
            1. Ancestry set of bzr revision-ids.
            2. History list of bzr revision-ids. Similar to the result of
               bzrlib.Branch.revision_history().
            3. Dictionnary mapping bzr bzr revision-ids to the database ids of
               the corresponding BranchRevision rows for this branch.
        """

    def getInternalBzrUrl():
        """Get the internal URL for this branch.

        It's generally better to use `getBzrBranch` to open the branch
        directly, as that method is safe against the branch unexpectedly being
        a branch reference or stacked on something mischievous.
        """

    def getBzrBranch():
        """Return the BzrBranch for this database Branch.

        You can only call this if a server returned by `get_ro_server` or
        `get_rw_server` is running.

        :raise lp.codehosting.bzrutils.UnsafeUrlSeen: If the branch is stacked
            on or a reference to an unacceptable URL.
        """

    def getPullURL():
        """Return the URL used to pull the branch into the mirror area."""

    @export_write_operation()
    def requestMirror():
        """Request that this branch be mirrored on the next run of the branch
        puller.
        """

    def startMirroring():
        """Signal that this branch is being mirrored."""

    def branchChanged(stacked_on_url, last_revision_id, control_format,
                      branch_format, repository_format):
        """Record that a branch has been changed.

        This method records the stacked on branch tip revision id and format
        or the branch and creates a scan job if the tip revision id has
        changed.

        :param stacked_on_url: The unique name of the branch this branch is
            stacked on, or '' if this branch is not stacked.
        :param last_revision_id: The tip revision ID of the branch.
        :param control_format: The entry from ControlFormat for the branch.
        :param branch_format: The entry from BranchFormat for the branch.
        :param repository_format: The entry from RepositoryFormat for the
            branch.
        """

    def mirrorFailed(reason):
        """Signal that a mirror attempt failed.

        :param reason: An error message that will be displayed on the branch
            detail page.
        """

    def commitsForDays(since):
        """Get a list of commit counts for days since `since`.

        This method returns all commits for the branch, so this includes
        revisions brought in through merges.

        :return: A list of tuples like (date, count).
        """

    needs_upgrading = Attribute("Whether the branch needs to be upgraded.")
    upgrade_pending = Attribute(
        "Whether a branch has had an upgrade requested.")

    def requestUpgrade():
        """Create an IBranchUpgradeJob to upgrade this branch."""

    def visibleByUser(user):
        """Can the specified user see this branch?"""


class IBranchSet(Interface):
    """Interface representing the set of branches."""

    export_as_webservice_collection(IBranch)

    def countBranchesWithAssociatedBugs():
        """Return the number of branches that have bugs associated.

        Only counts public branches.
        """

    def getRecentlyChangedBranches(
        branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """Return a result set of branches that have been recently updated.

        Only HOSTED and MIRRORED branches are returned in the result set.

        If branch_count is specified, the result set will contain at most
        branch_count items.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        """

    def getRecentlyImportedBranches(
        branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """Return a result set of branches that have been recently imported.

        The result set only contains IMPORTED branches.

        If branch_count is specified, the result set will contain at most
        branch_count items.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        """

    def getRecentlyRegisteredBranches(
        branch_count=None,
        lifecycle_statuses=DEFAULT_BRANCH_STATUS_IN_LISTING,
        visible_by_user=None):
        """Return a result set of branches that have been recently registered.

        If branch_count is specified, the result set will contain at most
        branch_count items.

        If lifecycle_statuses evaluates to False then branches
        of any lifecycle_status are returned, otherwise only branches
        with a lifecycle_status of one of the lifecycle_statuses
        are returned.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        """

    @operation_parameters(
        unique_name=TextLine(title=_('Branch unique name'), required=True))
    @operation_returns_entry(IBranch)
    @export_read_operation()
    def getByUniqueName(unique_name):
        """Find a branch by its ~owner/product/name unique name.

        Return None if no match was found.
        """

    @operation_parameters(
        url=TextLine(title=_('Branch URL'), required=True))
    @operation_returns_entry(IBranch)
    @export_read_operation()
    def getByUrl(url):
        """Find a branch by URL.

        Either from the external specified in Branch.url, from the URL on
        http://bazaar.launchpad.net/ or the lp: URL.

        This is a frontend shim to `IBranchLookup.getByUrl` to allow it to be
        exported over the API. If you want to call this from within the
        Launchpad app, use the `IBranchLookup` version instead.

        Return None if no match was found.
        """

    @operation_parameters(
        urls=List(
            title=u'A list of URLs of branches',
            description=(
                u'These can be URLs external to '
                u'Launchpad, lp: URLs, or http://bazaar.launchpad.net/ URLs, '
                u'or any mix of all these different kinds.'),
            value_type=TextLine(),
            required=True))
    @export_read_operation()
    def getByUrls(urls):
        """Finds branches by URL.

        Either from the external specified in Branch.url, from the URL on
        http://bazaar.launchpad.net/, or from the lp: URL.

        This is a frontend shim to `IBranchLookup.getByUrls` to allow it to be
        exported over the API. If you want to call this from within the
        Launchpad app, use the `IBranchLookup` version instead.

        :param urls: An iterable of URLs expressed as strings.
        :return: A dictionary mapping URLs to branches. If the URL has no
            associated branch, the URL will map to `None`.
        """

    @collection_default_content()
    def getBranches(limit=50):
        """Return a collection of branches."""


class IBranchListingQueryOptimiser(Interface):
    """Interface for a helper utility to do efficient queries for branches.

    Branch listings show several pieces of information and need to do batch
    queries to the database to avoid many small queries.

    Instead of having branch related queries scattered over other utility
    objects, this interface and utility object brings them together.
    """

    def getProductSeriesForBranches(branch_ids):
        """Return the ProductSeries associated with the branch_ids.

        :param branch_ids: a list of branch ids.
        :return: a list of `ProductSeries` objects.
        """

    def getOfficialSourcePackageLinksForBranches(branch_ids):
        """The SeriesSourcePackageBranches associated with the branch_ids.

        :param branch_ids: a list of branch ids.
        :return: a list of `SeriesSourcePackageBranch` objects.
        """


class IBranchDelta(Interface):
    """The quantitative changes made to a branch that was edited or altered.
    """

    branch = Attribute("The IBranch, after it's been edited.")
    user = Attribute("The IPerson that did the editing.")

    # fields on the branch itself, we provide just the new changed value
    name = Attribute("Old and new names or None.")
    title = Attribute("Old and new branch titles or None.")
    summary = Attribute("The branch summary or None.")
    url = Attribute("Old and new branch URLs or None.")
    whiteboard = Attribute("The branch whiteboard or None.")
    lifecycle_status = Attribute("Old and new lifecycle status, or None.")
    revision_count = Attribute("Old and new revision counts, or None.")
    last_scanned_id = Attribute("The revision id of the tip revision.")


class IBranchCloud(Interface):
    """A utility to generate data for branch clouds.

    A branch cloud is a tag cloud of products, sized and styled based on the
    branches in those products.
    """

    def getProductsWithInfo(num_products=None):
        """Get products with their branch activity information.

        :return: a `ResultSet` of (product, num_branches, last_revision_date).
        """


class BzrIdentityMixin:
    """This mixin class determines the bazaar identities.

    Used by both the model branch class and the browser branch listing item.
    This allows the browser code to cache the associated links which reduces
    query counts.
    """

    @property
    def bzr_identity(self):
        """See `IBranch`."""
        identity, context = self.branchIdentities()[0]
        return identity

    def branchIdentities(self):
        """See `IBranch`."""
        lp_prefix = config.codehosting.bzr_lp_prefix
        if self.private or not self.target.supports_short_identites:
            # XXX: thumper 2010-04-08, bug 261609
            # We have to get around to fixing this
            identities = []
        else:
            identities = [
                (lp_prefix + link.bzr_path, link.context)
                for link in self.branchLinks()]
        identities.append((lp_prefix + self.unique_name, self))
        return identities

    def branchLinks(self):
        """See `IBranch`."""
        links = []
        for suite_sp in self.associatedSuiteSourcePackages():
            links.append(ICanHasLinkedBranch(suite_sp))
            if (suite_sp.distribution.currentseries == suite_sp.distroseries
                and suite_sp.pocket == PackagePublishingPocket.RELEASE):
                links.append(ICanHasLinkedBranch(
                        suite_sp.sourcepackage.distribution_sourcepackage))
        for series in self.associatedProductSeries():
            links.append(ICanHasLinkedBranch(series))
            if series.product.development_focus == series:
                links.append(ICanHasLinkedBranch(series.product))
        return sorted(links)


def user_has_special_branch_access(user):
    """Admins and bazaar experts have special access.

    :param user: A 'Person' or None.
    """
    if user is None:
        return False
    celebs = getUtility(ILaunchpadCelebrities)
    return user.inTeam(celebs.admin) or user.inTeam(celebs.bazaar_experts)
