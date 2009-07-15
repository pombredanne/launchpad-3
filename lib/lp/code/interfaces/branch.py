# Copyright 2005, 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213,F0401,W0611

"""Branch interfaces."""

__metaclass__ = type

__all__ = [
    'bazaar_identity',
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
    'BranchTypeError',
    'CannotDeleteBranch',
    'DEFAULT_BRANCH_STATUS_IN_LISTING',
    'get_blacklisted_hostnames',
    'IBranch',
    'IBranchBatchNavigator',
    'IBranchCloud',
    'IBranchDelta',
    'IBranchBatchNavigator',
    'IBranchNavigationMenu',
    'IBranchSet',
    'NoSuchBranch',
    'UnknownBranchTypeError',
    'user_has_special_branch_access',
    ]

from cgi import escape
from operator import attrgetter
import re

from zope.component import getUtility
from zope.interface import Interface, Attribute
from zope.schema import (
    Bool, Int, Choice, Text, TextLine, Datetime)

from lazr.restful.fields import CollectionField, Reference, ReferenceChoice
from lazr.restful.declarations import (
    call_with, collection_default_content, export_as_webservice_collection,
    export_as_webservice_entry, export_read_operation, export_write_operation,
    exported, operation_parameters, operation_returns_entry, REQUEST_USER)

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
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.role import IHasOwner
from lp.registry.interfaces.person import IPerson
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

    def __init__(self, existing_branch):
        # XXX: JonathanLange 2008-12-04 spec=package-branches: This error
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


class CannotDeleteBranch(Exception):
    """The branch cannot be deleted at this time."""


class UnknownBranchTypeError(Exception):
    """Raised when the user specifies an unrecognized branch type."""


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
        input = super(BranchURIField, self).normalize(input)
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

        super(BranchURIField, self)._validate(value)

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


class IBranch(IHasOwner, IHasBranchTarget):
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

    private = exported(
        Bool(
            title=_("Keep branch confidential"), required=False,
            readonly=True, default=False,
            description=_(
                "Make this branch visible only to its subscribers.")))

    @operation_parameters(
        private=Bool(title=_("Keep branch confidential")))
    @export_write_operation()
    def setPrivate(private):
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
            required=True,
            vocabulary='UserTeamsParticipationPlusSelf',
            description=_("Either yourself or a team you are a member of. "
                          "This controls who can modify the branch.")))

    reviewer = exported(
        PublicPersonChoice(
            title=_('Default Review Team'),
            required=False,
            vocabulary='ValidPersonOrTeam',
            description=_("The reviewer of a branch is the person or team "
                          "that is responsible for reviewing proposals and "
                          "merging into this branch.")))

    # XXX: JonathanLange 2008-11-24: Export these.
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

    sourcepackage = Attribute(
        "The ISourcePackage that this branch belongs to. None if not a "
        "package branch.")

    code_reviewer = Attribute(
        "The reviewer if set, otherwise the owner of the branch.")

    namespace = Attribute(
        "The namespace of this branch, as an `IBranchNamespace`.")

    # Product attributes
    # ReferenceChoice is Interface rather than IProduct as IProduct imports
    # IBranch and we'd get import errors.  IPerson does a similar trick.
    # The schema is set properly to `IProduct` in _schema_circular_imports.
    product = exported(
        ReferenceChoice(
            title=_('Project'),
            required=False,
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

    warehouse_url = Attribute(
        "URL for accessing the branch by ID. "
        "This is for in-datacentre services only and allows such services to "
        "be unaffected during branch renames. "
        "See doc/bazaar for more information about the branch warehouse.")

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

    def addLandingTarget(registrant, target_branch, dependent_branch=None,
                         whiteboard=None, date_created=None,
                         needs_review=False, initial_comment=None,
                         review_requests=None):
        """Create a new BranchMergeProposal with this branch as the source.

        Both the target_branch and the dependent_branch, if it is there,
        must be branches of the same project as the source branch.

        Branches without associated projects, junk branches, cannot
        specify landing targets.

        :param registrant: The person who is adding the landing target.
        :param target_branch: Must be another branch, and different to self.
        :param dependent_branch: Optional but if it is not None, it must be
            another branch.
        :param whiteboard: Optional.  Just text, notes or instructions
            pertinant to the landing such as testing notes.
        :param date_created: Used to specify the date_created value of the
            merge request.
        :param needs_review: Used to specify the proposal is ready for
            review right now.
        :param initial_comment: An optional initial comment can be added
            when adding the new target.
        :param review_requests: An optional list of (`Person`, review_type).
        """

    def getStackedBranches():
        """The branches that are stacked on this one."""

    def getStackedBranchesWithIncompleteMirrors():
        """Branches that are stacked on this one but aren't done mirroring.

        In particular, these are branches that have started mirroring but have
        not yet succeeded. Failed branches are included.
        """

    merge_queue = Attribute(
        "The queue that contains the QUEUED proposals for this branch.")

    merge_control_status = Choice(
        title=_('Merge Control Status'), required=True,
        vocabulary=BranchMergeControlStatus,
        default=BranchMergeControlStatus.NO_QUEUE)

    def getMergeQueue():
        """The proposals that are QUEUED to land on this branch."""

    def revisions_since(timestamp):
        """Revisions in the history that are more recent than timestamp."""

    code_is_browseable = Attribute(
        "Is the code in this branch accessable through codebrowse?")

    def codebrowse_url(*extras):
        """Construct a URL for this branch in codebrowse.

        :param extras: Zero or more path segments that will be joined onto the
            end of the URL (with `bzrlib.urlutils.join`).
        """

    # Don't use Object -- that would cause an import loop with ICodeImport.
    code_import = Attribute("The associated CodeImport, if any.")

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
                'lp:~user/product/branch-name.'
                )))

    def addToLaunchBag(launchbag):
        """Add information about this branch to `launchbag'.

        Use this when traversing to this branch in the web UI.

        In particular, add information about the branch's target to the
        launchbag. If the branch has a product, add that; if it has a source
        package, add lots of information about that.

        :param launchbag: `ILaunchBag`.
        """

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

    def associatedSuiteSourcePackages():
        """Return the suite source packages that this branch is linked to."""

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
    @export_write_operation()
    def subscribe(person, notification_level, max_diff_lines,
                  code_review_level):
        """Subscribe this person to the branch.

        :param person: The `Person` to subscribe.
        :param notification_level: The kinds of branch changes that cause
            notification.
        :param max_diff_lines: The maximum number of lines of diff that may
            appear in a notification.
        :param code_review_level: The kinds of code review activity that cause
            notification.
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
    @export_write_operation()
    def unsubscribe(person):
        """Remove the person's subscription to this branch."""

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

    def getPullURL():
        """Return the URL used to pull the branch into the mirror area."""

    @export_write_operation()
    def requestMirror():
        """Request that this branch be mirrored on the next run of the branch
        puller.
        """

    def startMirroring():
        """Signal that this branch is being mirrored."""

    def mirrorComplete(last_revision_id):
        """Signal that a mirror attempt has completed successfully.

        :param last_revision_id: The revision ID of the tip of the mirrored
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

    def getLatestBranchesForProduct(product, quantity, visible_by_user=None):
        """Return the most recently created branches for the product.

        At most `quantity` branches are returned. Branches that have been
        merged or abandoned don't appear in the results -- only branches that
        match `DEFAULT_BRANCH_STATUS_IN_LISTING`.

        :param visible_by_user: If a person is not supplied, only public
            branches are returned.  If a person is supplied both public
            branches, and the private branches that the person is entitled to
            see are returned.  Private branches are only visible to the owner
            and subscribers of the branch, and to LP admins.
        :type visible_by_user: `IPerson` or None
        """
        # XXX: JonathanLange 2008-11-27 spec=package-branches: This API needs
        # to change for source package branches.

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

        Return None if no match was found.
        """

    @collection_default_content()
    def getBranches(limit=50):
        """Return a collection of branches."""


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


def bazaar_identity(branch, is_dev_focus):
    """Return the shortest lp: style branch identity."""
    lp_prefix = config.codehosting.bzr_lp_prefix

    # XXX: TimPenhey 2008-05-06 bug=227602: Since at this stage the launchpad
    # name resolution is not authenticated, we can't resolve series branches
    # that end up pointing to private branches, so don't show short names for
    # the branch if it is private.
    if branch.private:
        return lp_prefix + branch.unique_name

    use_series = None
    # XXX: JonathanLange 2009-03-21 spec=package-branches: This should
    # probably delegate to IBranch.target. I would do it now if I could figure
    # what all the optimization code is for.
    if branch.product is not None:
        if is_dev_focus:
            return lp_prefix + branch.product.name

        # If there are no associated series, then use the unique name.
        associated_series = sorted(
            branch.associatedProductSeries(), key=attrgetter('datecreated'))
        if len(associated_series) == 0:
            return lp_prefix + branch.unique_name
        # Use the most recently created series.
        use_series = associated_series[-1]
        return "%(prefix)s%(product)s/%(series)s" % {
            'prefix': lp_prefix,
            'product': use_series.product.name,
            'series': use_series.name}

    if branch.sourcepackage is not None:
        suite_sourcepackages = branch.associatedSuiteSourcePackages()
        # Take the first link if there is one.
        if len(suite_sourcepackages) > 0:
            suite_source_package = suite_sourcepackages[0]
            return lp_prefix + suite_source_package.path

    return lp_prefix + branch.unique_name


def user_has_special_branch_access(user):
    """Admins and bazaar experts have special access.

    :param user: A 'Person' or None.
    """
    if user is None:
        return False
    celebs = getUtility(ILaunchpadCelebrities)
    return user.inTeam(celebs.admin) or user.inTeam(celebs.bazaar_experts)
