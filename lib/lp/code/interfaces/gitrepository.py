# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git repository interfaces."""

__metaclass__ = type

__all__ = [
    'GitIdentityMixin',
    'GIT_REPOSITORY_NAME_VALIDATION_ERROR_MESSAGE',
    'git_repository_name_validator',
    'IGitRepository',
    'IGitRepositoryDelta',
    'IGitRepositorySet',
    'user_has_special_git_repository_access',
    ]

import re

from lazr.lifecycle.snapshot import doNotSnapshot
from lazr.restful.declarations import (
    call_with,
    collection_default_content,
    export_as_webservice_collection,
    export_as_webservice_entry,
    export_destructor_operation,
    export_read_operation,
    export_write_operation,
    exported,
    mutator_for,
    operation_for_version,
    operation_parameters,
    operation_returns_collection_of,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from lazr.restful.interface import copy_field
from zope.component import getUtility
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    List,
    Text,
    TextLine,
    )

from lp import _
from lp.app.enums import InformationType
from lp.app.validators import LaunchpadValidationError
from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.code.interfaces.defaultgit import ICanHasDefaultGitRepository
from lp.code.interfaces.hasgitrepositories import IHasGitRepositories
from lp.code.interfaces.hasrecipes import IHasRecipes
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.persondistributionsourcepackage import (
    IPersonDistributionSourcePackageFactory,
    )
from lp.registry.interfaces.personproduct import IPersonProductFactory
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.role import IPersonRoles
from lp.services.fields import (
    PersonChoice,
    PublicPersonChoice,
    )
from lp.services.webhooks.interfaces import IWebhookTarget


GIT_REPOSITORY_NAME_VALIDATION_ERROR_MESSAGE = _(
    "Git repository names must start with a number or letter.  The characters "
    "+, -, _, . and @ are also allowed after the first character.  Repository "
    "names must not end with \".git\".")


# This is a copy of the pattern in database/schema/patch-2209-61-0.sql.
# Don't change it without changing that.
valid_git_repository_name_pattern = re.compile(
    r"^(?i)[a-z0-9][a-z0-9+\.\-@_]*\Z")


def valid_git_repository_name(name):
    """Return True iff the name is valid as a Git repository name.

    The rules for what is a valid Git repository name are described in
    GIT_REPOSITORY_NAME_VALIDATION_ERROR_MESSAGE.
    """
    if (not name.endswith(".git") and
        valid_git_repository_name_pattern.match(name)):
        return True
    return False


def git_repository_name_validator(name):
    """Return True if the name is valid, or raise a LaunchpadValidationError.
    """
    if not valid_git_repository_name(name):
        raise LaunchpadValidationError(
            _("Invalid Git repository name '${name}'. ${message}",
              mapping={
                  "name": name,
                  "message": GIT_REPOSITORY_NAME_VALIDATION_ERROR_MESSAGE,
                  }))
    return True


class IGitRepositoryView(IHasRecipes):
    """IGitRepository attributes that require launchpad.View permission."""

    id = Int(title=_("ID"), readonly=True, required=True)

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    registrant = exported(PublicPersonChoice(
        title=_("Registrant"), required=True, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person who registered this Git repository.")))

    owner = exported(PersonChoice(
        title=_("Owner"), required=True, readonly=True,
        vocabulary="AllUserTeamsParticipationPlusSelf",
        description=_(
            "The owner of this Git repository. This controls who can modify "
            "the repository.")))

    target = exported(
        Reference(
            title=_("Target"), required=True, readonly=True,
            schema=IHasGitRepositories,
            description=_("The target of the repository.")),
        as_of="devel")

    namespace = Attribute(
        "The namespace of this repository, as an `IGitNamespace`.")

    # XXX cjwatson 2015-01-29: Add some advice about default repository
    # naming.
    name = exported(TextLine(
        title=_("Name"), required=True, readonly=True,
        constraint=git_repository_name_validator,
        description=_(
            "The repository name. Keep very short, unique, and descriptive, "
            "because it will be used in URLs.")))

    information_type = exported(Choice(
        title=_("Information type"), vocabulary=InformationType,
        required=True, readonly=True, default=InformationType.PUBLIC,
        description=_(
            "The type of information contained in this repository.")))

    owner_default = exported(Bool(
        title=_("Owner default"), required=True, readonly=True,
        description=_(
            "Whether this repository is the default for its owner and "
            "target.")))

    target_default = exported(Bool(
        title=_("Target default"), required=True, readonly=True,
        description=_(
            "Whether this repository is the default for its target.")))

    unique_name = exported(Text(
        title=_("Unique name"), readonly=True,
        description=_(
            "Unique name of the repository, including the owner and project "
            "names.")))

    display_name = exported(Text(
        title=_("Display name"), readonly=True,
        description=_("Display name of the repository.")))

    code_reviewer = Attribute(
        "The reviewer if set, otherwise the owner of the repository.")

    shortened_path = Attribute(
        "The shortest reasonable version of the path to this repository.")

    @operation_parameters(
        reviewer=Reference(
            title=_("A person for which the reviewer status is in question."),
            schema=IPerson))
    @export_read_operation()
    @operation_for_version('devel')
    def isPersonTrustedReviewer(reviewer):
        """Return true if the `reviewer` is a trusted reviewer.

        The reviewer is trusted if they either own the repository, or are in
        the team that owns the repository, or they are in the review team
        for the repository.
        """

    git_identity = exported(Text(
        title=_("Git identity"), readonly=True,
        description=_(
            "If this is the default repository for some target, then this is "
            "'lp:' plus a shortcut version of the path via that target.  "
            "Otherwise it is simply 'lp:' plus the unique name.")))

    identity = Attribute(
        "The identity of this repository: a VCS-independent synonym for "
        "git_identity.")

    git_https_url = exported(TextLine(
        title=_("HTTPS URL"), readonly=True,
        description=_(
            "An HTTPS URL for this repository, or None in the case of private "
            "repositories.")))

    git_ssh_url = exported(TextLine(
        title=_("SSH URL"), readonly=True,
        description=_("A git+ssh:// URL for this repository.")))

    refs = exported(doNotSnapshot(CollectionField(
        title=_("The references present in this repository."),
        readonly=True,
        # Really IGitRef, patched in _schema_circular_imports.py.
        value_type=Reference(Interface))))

    branches = exported(doNotSnapshot(CollectionField(
        title=_("The branch references present in this repository."),
        readonly=True,
        # Really IGitRef, patched in _schema_circular_imports.py.
        value_type=Reference(Interface))))

    branches_by_date = Attribute(
        "The branch references present in this repository, ordered by last "
        "commit date.")

    subscriptions = exported(CollectionField(
        title=_("GitSubscriptions associated with this repository."),
        readonly=True,
        # Really IGitSubscription, patched in _schema_circular_imports.py.
        value_type=Reference(Interface)))

    subscribers = exported(CollectionField(
        title=_("Persons subscribed to this repository."),
        readonly=True, value_type=Reference(IPerson)))

    def getRefByPath(path):
        """Look up a single reference in this repository by path.

        :param path: A string to look up as a path.

        :return: An `IGitRef`, or None.
        """

    def createOrUpdateRefs(refs_info, get_objects=False, logger=None):
        """Create or update a set of references in this repository.

        :param refs_info: A dict mapping ref paths to
            {"sha1": sha1, "type": `GitObjectType`}.
        :param get_objects: Return the created/updated references.
        :param logger: An optional logger.

        :return: A list of the created/updated references if get_objects,
            otherwise None.
        """

    def removeRefs(paths):
        """Remove a set of references in this repository.

        :params paths: An iterable of paths.
        """

    def planRefChanges(hosting_path, logger=None):
        """Plan ref changes based on information from the hosting service.

        :param hosting_path: A path on the hosting service.
        :param logger: An optional logger.

        :return: A dict of refs to create or update as appropriate, mapping
            ref paths to dictionaries of their fields; and a set of ref
            paths to remove.
        """

    def fetchRefCommits(hosting_path, refs, logger=None):
        """Fetch commit information from the hosting service for a set of refs.

        :param hosting_path: A path on the hosting service.
        :param refs: A dict mapping ref paths to dictionaries of their
            fields; the field dictionaries will be updated with any detailed
            commit information that is available.
        :param logger: An optional logger.
        """

    def synchroniseRefs(refs_to_upsert, refs_to_remove, logger=None):
        """Synchronise references with those from the hosting service.

        :param refs_to_upsert: A dictionary mapping ref paths to
            dictionaries of their fields; these refs will be created or
            updated as appropriate.
        :param refs_to_remove: A set of ref paths to remove.
        :param logger: An optional logger.
        """

    def setOwnerDefault(value):
        """Set whether this repository is the default for its owner-target.

        This is for internal use; the caller should ensure permission to
        edit the owner, should arrange to remove any existing owner-target
        default, and should check that this repository is attached to the
        desired target.

        :param value: True if this repository should be the owner-target
            default, otherwise False.
        """

    def setTargetDefault(value):
        """Set whether this repository is the default for its target.

        This is for internal use; the caller should ensure permission to
        edit the target, should arrange to remove any existing target
        default, and should check that this repository is attached to the
        desired target.

        :param value: True if this repository should be the target default,
            otherwise False.
        """

    def getCodebrowseUrl():
        """Construct a browsing URL for this Git repository."""

    def getCodebrowseUrlForRevision(commit):
        """The URL to the commit of the merge to the target branch"""

    def visibleByUser(user):
        """Can the specified user see this repository?"""

    def getAllowedInformationTypes(user):
        """Get a list of acceptable `InformationType`s for this repository.

        If the user is a Launchpad admin, any type is acceptable.
        """

    def getInternalPath():
        """Get the internal path to this repository.

        This is used on the storage backend.
        """

    def getRepositoryDefaults():
        """Return a sorted list of `ICanHasDefaultGitRepository` objects.

        There is one result for each related object for which this
        repository is the default.  For example, in the case where a
        repository is the default for a project and is also its owner's
        default repository for that project, the objects for both the
        project and the person-project are returned.

        More important related objects are sorted first.
        """

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    def getRepositoryIdentities():
        """A list of aliases for a repository.

        Returns a list of tuples of path and context object.  There is at
        least one alias for any repository, and that is the repository
        itself.  For default repositories, the context object is the
        appropriate default object.

        Where a repository is the default for a product or a distribution
        source package, the repository is available through a number of
        different URLs.  These URLs are the aliases for the repository.

        For example, a repository which is the default for the 'fooix'
        project and which is also its owner's default repository for that
        project is accessible using:
          fooix - the context object is the project fooix
          ~fooix-owner/fooix - the context object is the person-project
              ~fooix-owner and fooix
          ~fooix-owner/fooix/+git/fooix - the unique name of the repository
              where the context object is the repository itself.
        """

    def userCanBeSubscribed(person):
        """Return True if the `IPerson` can be subscribed to the repository."""

    @operation_parameters(
        person=Reference(title=_("The person to subscribe."), schema=IPerson),
        notification_level=Choice(
            title=_("The level of notification to subscribe to."),
            vocabulary=BranchSubscriptionNotificationLevel),
        max_diff_lines=Choice(
            title=_("The max number of lines for diff email."),
            vocabulary=BranchSubscriptionDiffSize),
        code_review_level=Choice(
            title=_("The level of code review notification emails."),
            vocabulary=CodeReviewNotificationLevel))
    # Really IGitSubscription, patched in _schema_circular_imports.py.
    @operation_returns_entry(Interface)
    @call_with(subscribed_by=REQUEST_USER)
    @export_write_operation()
    @operation_for_version("devel")
    def subscribe(person, notification_level, max_diff_lines,
                  code_review_level, subscribed_by):
        """Subscribe this person to the repository.

        :param person: The `Person` to subscribe.
        :param notification_level: The kinds of repository changes that
            cause notification.
        :param max_diff_lines: The maximum number of lines of diff that may
            appear in a notification.
        :param code_review_level: The kinds of code review activity that
            cause notification.
        :param subscribed_by: The person who is subscribing the subscriber.
            Most often the subscriber themselves.
        :return: A new or existing `GitSubscription`.
        """

    @operation_parameters(
        person=Reference(title=_("The person to search for"), schema=IPerson))
    # Really IGitSubscription, patched in _schema_circular_imports.py.
    @operation_returns_entry(Interface)
    @export_read_operation()
    @operation_for_version("devel")
    def getSubscription(person):
        """Return the `GitSubscription` for this person."""

    def hasSubscription(person):
        """Is this person subscribed to the repository?"""

    @operation_parameters(
        person=Reference(title=_("The person to unsubscribe"), schema=IPerson))
    @call_with(unsubscribed_by=REQUEST_USER)
    @export_write_operation()
    @operation_for_version("devel")
    def unsubscribe(person, unsubscribed_by):
        """Remove the person's subscription to this repository.

        :param person: The person or team to unsubscribe from the repository.
        :param unsubscribed_by: The person doing the unsubscribing.
        """

    def getSubscriptionsByLevel(notification_levels):
        """Return the subscriptions that are at the given notification levels.

        :param notification_levels: An iterable of
            `BranchSubscriptionNotificationLevel`s.
        :return: A `ResultSet`.
        """

    def getNotificationRecipients():
        """Return a complete INotificationRecipientSet instance.

        The INotificationRecipientSet instance contains the subscribers
        and their subscriptions.
        """

    landing_targets = exported(CollectionField(
        title=_("Landing targets"),
        description=_(
            "A collection of the merge proposals where this repository is the "
            "source."),
        readonly=True,
        # Really IBranchMergeProposal, patched in _schema_circular_imports.py.
        value_type=Reference(Interface)))
    landing_candidates = exported(CollectionField(
        title=_("Landing candidates"),
        description=_(
            "A collection of the merge proposals where this repository is the "
            "target."),
        readonly=True,
        # Really IBranchMergeProposal, patched in _schema_circular_imports.py.
        value_type=Reference(Interface)))
    dependent_landings = exported(CollectionField(
        title=_("Dependent landings"),
        description=_(
            "A collection of the merge proposals that are dependent on this "
            "repository."),
        readonly=True,
        # Really IBranchMergeProposal, patched in _schema_circular_imports.py.
        value_type=Reference(Interface)))

    def getMergeProposalByID(id):
        """Return this repository's merge proposal with this id, or None."""

    def isRepositoryMergeable(other):
        """Is the other repository mergeable into this one (or vice versa)?"""

    pending_writes = Attribute(
        "Whether there are recent changes in this repository that have not "
        "yet been scanned.")

    def updateMergeCommitIDs(paths):
        """Update commit SHA1s of merge proposals for this repository.

        The *_git_commit_sha1 columns of merge proposals are stored
        explicitly in order that merge proposals are still meaningful after
        associated refs have been deleted.  However, active merge proposals
        where the refs in question still exist should have these columns
        kept up to date.
        """

    def scheduleDiffUpdates(paths):
        """Create UpdatePreviewDiffJobs for landing targets.

        :param paths: A list of reference paths.  Any merge proposals whose
            source is this repository and one of these paths will have their
            diffs updated.
        """

    def markRecipesStale(paths):
        """Mark recipes associated with this repository as stale.

        :param paths: A list of reference paths.  Any recipes that include
            an entry that points to this repository and that has a `revspec`
            that is one of these paths will be marked as stale.
        """

    def detectMerges(paths, logger=None):
        """Detect merges of landing candidates.

        :param paths: A list of reference paths.  Any merge proposals whose
            target is this repository and one of these paths will be
            checked.
        :param logger: An optional logger.
        """

    @operation_parameters(
        filename=TextLine(
            title=_("Relative path of file in the repository."),
            required=True),
        rev=TextLine(title=_("An optional revision. Defaults to 'HEAD'.")),
        )
    @export_read_operation()
    @operation_for_version("devel")
    def getBlob(filename, rev=None):
        """Get a blob by file name from this repository.

        :param filename: Relative path of a file in the repository.
        :param rev: An optional revision. Defaults to 'HEAD'.
        :return: A dict with keys 'data' and 'size'.
        """


class IGitRepositoryModerateAttributes(Interface):
    """IGitRepository attributes that can be edited by more than one community.
    """

    date_last_modified = exported(Datetime(
        title=_("Date last modified"), required=True, readonly=True))

    reviewer = exported(PublicPersonChoice(
        title=_("Review Team"), required=False, readonly=False,
        vocabulary="ValidBranchReviewer",
        description=_("The reviewer of a repository is the person or "
                      "exclusive team that is responsible for reviewing "
                      "proposals and merging into this repository.")))

    description = exported(Text(
        title=_("Description"), required=False, readonly=False,
        description=_("A short description of this repository.")))


class IGitRepositoryModerate(Interface):
    """IGitRepository methods that can be called by more than one community."""

    @mutator_for(IGitRepositoryView["information_type"])
    @operation_parameters(
        information_type=copy_field(IGitRepositoryView["information_type"]),
        )
    @call_with(user=REQUEST_USER)
    @export_write_operation()
    @operation_for_version("devel")
    def transitionToInformationType(information_type, user,
                                    verify_policy=True):
        """Set the information type for this repository.

        :param information_type: The `InformationType` to transition to.
        :param user: The `IPerson` who is making the change.
        :param verify_policy: Check if the new information type complies
            with the `IGitNamespacePolicy`.
        """


class IGitRepositoryEditableAttributes(Interface):
    """IGitRepository attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """

    default_branch = exported(TextLine(
        title=_("Default branch"), required=False, readonly=False,
        description=_(
            "The full path to the default branch for this repository, e.g. "
            "refs/heads/master.")))


class IGitRepositoryEdit(IWebhookTarget):
    """IGitRepository methods that require launchpad.Edit permission."""

    @mutator_for(IGitRepositoryView["name"])
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        new_name=TextLine(title=_("The new name of the repository.")))
    @export_write_operation()
    @operation_for_version("devel")
    def setName(new_name, user):
        """Set the name of the repository to be `new_name`."""

    @mutator_for(IGitRepositoryView["owner"])
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        new_owner=Reference(
            title=_("The new owner of the repository."), schema=IPerson))
    @export_write_operation()
    @operation_for_version("devel")
    def setOwner(new_owner, user):
        """Set the owner of the repository to be `new_owner`."""

    @mutator_for(IGitRepositoryView["target"])
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        target=Reference(
            title=_(
                "The project, distribution source package, or person the "
                "repository belongs to."),
            schema=IHasGitRepositories, required=True))
    @export_write_operation()
    @operation_for_version("devel")
    def setTarget(target, user):
        """Set the target of the repository."""

    @export_read_operation()
    @operation_for_version("devel")
    def canBeDeleted():
        """Can this repository be deleted in its current state?

        A repository is considered deletable if it is not linked to any
        merge proposals.
        """

    def getDeletionRequirements():
        """Determine what is required to delete this branch.

        :return: a dict of {object: (operation, reason)}, where object is the
            object that must be deleted or altered, operation is either
            "delete" or "alter", and reason is a string explaining why the
            object needs to be touched.
        """

    @call_with(break_references=True)
    @export_destructor_operation()
    @operation_for_version("devel")
    def destroySelf(break_references=False):
        """Delete the specified repository.

        :param break_references: If supplied, break any references to this
            repository by deleting items with mandatory references and
            NULLing other references.
        :raise: CannotDeleteGitRepository if the repository cannot be deleted.
        """


class IGitRepository(IGitRepositoryView, IGitRepositoryModerateAttributes,
                     IGitRepositoryModerate, IGitRepositoryEditableAttributes,
                     IGitRepositoryEdit):
    """A Git repository."""

    # Mark repositories as exported entries for the Launchpad API.
    # XXX cjwatson 2015-01-19 bug=760849: "beta" is a lie to get WADL
    # generation working.  Individual attributes must set their version to
    # "devel".
    export_as_webservice_entry(plural_name="git_repositories", as_of="beta")

    private = exported(Bool(
        title=_("Private"), required=False, readonly=True,
        description=_("This repository is visible only to its subscribers.")))


class IGitRepositorySet(Interface):
    """Interface representing the set of Git repositories."""

    export_as_webservice_collection(IGitRepository)

    def new(registrant, owner, target, name, information_type=None,
            date_created=None):
        """Create a Git repository and return it.

        :param registrant: The `IPerson` who registered the new repository.
        :param owner: The `IPerson` who owns the new repository.
        :param target: The `IProduct`, `IDistributionSourcePackage`, or
            `IPerson` that the new repository is associated with.
        :param name: The repository name.
        :param information_type: Set the repository's information type to
            one different from the target's default.  The type must conform
            to the target's code sharing policy.  (optional)
        """

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    @call_with(user=REQUEST_USER)
    @operation_parameters(
        path=TextLine(title=_("Repository path"), required=True))
    @operation_returns_entry(IGitRepository)
    @export_read_operation()
    @operation_for_version("devel")
    def getByPath(user, path):
        """Find a repository by its path.

        Any of these forms may be used::

            Unique names:
                ~OWNER/PROJECT/+git/NAME
                ~OWNER/DISTRO/+source/SOURCE/+git/NAME
                ~OWNER/+git/NAME
            Owner-target default aliases:
                ~OWNER/PROJECT
                ~OWNER/DISTRO/+source/SOURCE
            Official aliases:
                PROJECT
                DISTRO/+source/SOURCE

        Return None if no match was found.
        """

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        target=Reference(
            title=_("Target"), required=True, schema=IHasGitRepositories))
    @operation_returns_collection_of(IGitRepository)
    @export_read_operation()
    @operation_for_version("devel")
    def getRepositories(user, target):
        """Get all repositories for a target.

        :param user: An `IPerson`.  Only repositories visible by this user
            will be returned.
        :param target: An `IHasGitRepositories`.

        :return: A collection of `IGitRepository` objects.
        """

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        person=Reference(
            title=_("The person whose repository visibility is being "
                    "checked."),
            schema=IPerson),
        repository_names=List(value_type=Text(),
            title=_('List of repository unique names'), required=True),
    )
    @export_read_operation()
    @operation_for_version("devel")
    def getRepositoryVisibilityInfo(user, person, repository_names):
        """Return the named repositories visible to both user and person.

        Anonymous requesters don't get any information.

        :param user: The user requesting the information. If the user is
            None then we return an empty dict.
        :param person: The person whose repository visibility we wish to
            check.
        :param repository_names: The unique names of the repositories to
            check.

        Return a dict with the following values:
        person_name: the displayname of the person.
        visible_repositories: a list of the unique names of the repositories
        which the requester and specified person can both see.

        This API call is provided for use by the client Javascript.  It is
        not designed to efficiently scale to handle requests for large
        numbers of repositories.
        """

    @operation_parameters(
        target=Reference(
            title=_("Target"), required=True, schema=IHasGitRepositories))
    @operation_returns_entry(IGitRepository)
    @export_read_operation()
    @operation_for_version("devel")
    def getDefaultRepository(target):
        """Get the default repository for a target.

        :param target: An `IHasGitRepositories`.

        :raises GitTargetError: if `target` is an `IPerson`.
        :return: An `IGitRepository`, or None.
        """

    @operation_parameters(
        owner=Reference(title=_("Owner"), required=True, schema=IPerson),
        target=Reference(
            title=_("Target"), required=True, schema=IHasGitRepositories))
    @operation_returns_entry(IGitRepository)
    @export_read_operation()
    @operation_for_version("devel")
    def getDefaultRepositoryForOwner(owner, target):
        """Get a person's default repository for a target.

        :param owner: An `IPerson`.
        :param target: An `IHasGitRepositories`.

        :raises GitTargetError: if `target` is an `IPerson`.
        :return: An `IGitRepository`, or None.
        """

    @operation_parameters(
        target=Reference(
            title=_("Target"), required=True, schema=IHasGitRepositories),
        repository=Reference(
            title=_("Git repository"), required=False, schema=IGitRepository))
    @export_write_operation()
    @operation_for_version("devel")
    def setDefaultRepository(target, repository):
        """Set the default repository for a target.

        :param target: An `IHasGitRepositories`.
        :param repository: An `IGitRepository`, or None to unset the default
            repository.

        :raises GitTargetError: if `target` is an `IPerson`.
        """

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        owner=Reference(title=_("Owner"), required=True, schema=IPerson),
        target=Reference(
            title=_("Target"), required=True, schema=IHasGitRepositories),
        repository=Reference(
            title=_("Git repository"), required=False, schema=IGitRepository))
    @export_write_operation()
    @operation_for_version("devel")
    def setDefaultRepositoryForOwner(owner, target, repository, user):
        """Set a person's default repository for a target.

        :param owner: An `IPerson`.
        :param target: An `IHasGitRepositories`.
        :param repository: An `IGitRepository`, or None to unset the default
            repository.
        :param user: The `IPerson` who is making the change.

        :raises GitTargetError: if `target` is an `IPerson`.
        """

    @collection_default_content()
    def empty_list():
        """Return an empty collection of repositories.

        This only exists to keep lazr.restful happy.
        """

    def preloadDefaultRepositoriesForProjects(projects):
        """Get preloaded default repositories for a list of projects.

        :return: A dict mapping project IDs to their default repositories.
            Projects that do not have default repositories are omitted.
        """


class IGitRepositoryDelta(Interface):
    """The quantitative changes made to a Git repository that was edited or
    altered.
    """

    repository = Attribute("The IGitRepository, after it's been edited.")
    user = Attribute("The IPerson that did the editing.")

    # fields on the repository itself, we provide just the new changed value
    name = Attribute("Old and new names or None.")
    identity = Attribute("Old and new identities or None.")


class GitIdentityMixin:
    """This mixin class determines Git repository paths.

    Used by both the model GitRepository class and the browser repository
    listing item.  This allows the browser code to cache the associated
    context objects which reduces query counts.
    """

    @property
    def shortened_path(self):
        """See `IGitRepository`."""
        path, context = self.getRepositoryIdentities()[0]
        return path

    @property
    def git_identity(self):
        """See `IGitRepository`."""
        return "lp:" + self.shortened_path

    identity = git_identity

    def getRepositoryDefaults(self):
        """See `IGitRepository`."""
        defaults = []
        if self.target_default:
            defaults.append(ICanHasDefaultGitRepository(self.target))
        if self.owner_default:
            if IProduct.providedBy(self.target):
                factory = getUtility(IPersonProductFactory)
                default = factory.create(self.owner, self.target)
            elif IDistributionSourcePackage.providedBy(self.target):
                factory = getUtility(IPersonDistributionSourcePackageFactory)
                default = factory.create(self.owner, self.target)
            else:
                # Also enforced by database constraint.
                raise AssertionError(
                    "Only projects or packages can have owner-target default "
                    "repositories.")
            defaults.append(ICanHasDefaultGitRepository(default))
        return sorted(defaults)

    def getRepositoryIdentities(self):
        """See `IGitRepository`."""
        identities = [
            (default.path, default.context)
            for default in self.getRepositoryDefaults()]
        identities.append((self.unique_name, self))
        return identities


def user_has_special_git_repository_access(user):
    """Admins have special access.

    :param user: An `IPerson` or None.
    """
    if user is None:
        return False
    roles = IPersonRoles(user)
    if roles.in_admin:
        return True
    return False
