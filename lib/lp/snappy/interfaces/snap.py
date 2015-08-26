# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap package interfaces."""

__metaclass__ = type

__all__ = [
    'CannotDeleteSnap',
    'DuplicateSnapName',
    'ISnap',
    'ISnapSet',
    'ISnapView',
    'NoSourceForSnap',
    'NoSuchSnap',
    'SNAP_FEATURE_FLAG',
    'SnapBuildAlreadyPending',
    'SnapBuildArchiveOwnerMismatch',
    'SnapBuildDisallowedArchitecture',
    'SnapFeatureDisabled',
    'SnapNotOwner',
    ]

import httplib

from lazr.lifecycle.snapshot import doNotSnapshot
from lazr.restful.declarations import (
    call_with,
    collection_default_content,
    error_status,
    export_as_webservice_collection,
    export_as_webservice_entry,
    export_destructor_operation,
    export_factory_operation,
    export_read_operation,
    export_write_operation,
    exported,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    ReferenceChoice,
    )
from zope.interface import Interface
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    List,
    Text,
    TextLine,
    )
from zope.security.interfaces import (
    Forbidden,
    Unauthorized,
    )

from lp import _
from lp.app.errors import NameLookupFailed
from lp.app.validators.name import name_validator
from lp.buildmaster.interfaces.processor import IProcessor
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.gitrepository import IGitRepository
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.role import IHasOwner
from lp.services.fields import (
    PersonChoice,
    PublicPersonChoice,
    )
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries


SNAP_FEATURE_FLAG = u"snap.allow_new"


@error_status(httplib.BAD_REQUEST)
class SnapBuildAlreadyPending(Exception):
    """A build was requested when an identical build was already pending."""

    def __init__(self):
        super(SnapBuildAlreadyPending, self).__init__(
            "An identical build of this snap package is already pending.")


@error_status(httplib.FORBIDDEN)
class SnapBuildArchiveOwnerMismatch(Forbidden):
    """Builds against private archives require that owners match.

    The snap package owner must have write permission on the archive, so
    that a malicious snap package build can't steal any secrets that its
    owner didn't already have access to.  Furthermore, we want to make sure
    that future changes to the team owning the snap package don't grant it
    retrospective access to information about a private archive.  For now,
    the simplest way to do this is to require that the owners match exactly.
    """

    def __init__(self):
        super(SnapBuildArchiveOwnerMismatch, self).__init__(
            "Snap package builds against private archives are only allowed "
            "if the snap package owner and the archive owner are equal.")


@error_status(httplib.BAD_REQUEST)
class SnapBuildDisallowedArchitecture(Exception):
    """A build was requested for a disallowed architecture."""

    def __init__(self, das):
        super(SnapBuildDisallowedArchitecture, self).__init__(
            "This snap package is not allowed to build for %s." %
            das.displayname)


@error_status(httplib.UNAUTHORIZED)
class SnapFeatureDisabled(Unauthorized):
    """Only certain users can create new snap-related objects."""

    def __init__(self):
        super(SnapFeatureDisabled, self).__init__(
            "You do not have permission to create new snaps or new snap "
            "builds.")


@error_status(httplib.BAD_REQUEST)
class DuplicateSnapName(Exception):
    """Raised for snap packages with duplicate name/owner."""

    def __init__(self):
        super(DuplicateSnapName, self).__init__(
            "There is already a snap package with the same name and owner.")


@error_status(httplib.UNAUTHORIZED)
class SnapNotOwner(Unauthorized):
    """The registrant/requester is not the owner or a member of its team."""


class NoSuchSnap(NameLookupFailed):
    """The requested snap package does not exist."""
    _message_prefix = "No such snap package with this owner"


@error_status(httplib.BAD_REQUEST)
class NoSourceForSnap(Exception):
    """Snap packages must have a source (Bazaar branch or Git repository)."""

    def __init__(self):
        super(NoSourceForSnap, self).__init__(
            "New snap packages must have either a Bazaar branch or a Git "
            "repository.")


@error_status(httplib.BAD_REQUEST)
class CannotDeleteSnap(Exception):
    """This snap package cannot be deleted."""


class ISnapView(Interface):
    """`ISnap` attributes that require launchpad.View permission."""

    id = Int(title=_("ID"), required=True, readonly=True)

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    registrant = exported(PublicPersonChoice(
        title=_("Registrant"), required=True, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person who registered this snap package.")))

    @call_with(requester=REQUEST_USER)
    @operation_parameters(
        archive=Reference(schema=IArchive),
        distro_arch_series=Reference(schema=IDistroArchSeries),
        pocket=Choice(vocabulary=PackagePublishingPocket))
    # Really ISnapBuild, patched in _schema_circular_imports.py.
    @export_factory_operation(Interface, [])
    @operation_for_version("devel")
    def requestBuild(requester, archive, distro_arch_series, pocket):
        """Request that the snap package be built.

        :param requester: The person requesting the build.
        :param archive: The IArchive to associate the build with.
        :param distro_arch_series: The architecture to build for.
        :param pocket: The pocket that should be targeted.
        :return: `ISnapBuild`.
        """

    builds = exported(doNotSnapshot(CollectionField(
        title=_("All builds of this snap package."),
        description=_(
            "All builds of this snap package, sorted in descending order "
            "of finishing (or starting if not completed successfully)."),
        # Really ISnapBuild, patched in _schema_circular_imports.py.
        value_type=Reference(schema=Interface), readonly=True)))

    completed_builds = exported(doNotSnapshot(CollectionField(
        title=_("Completed builds of this snap package."),
        description=_(
            "Completed builds of this snap package, sorted in descending "
            "order of finishing."),
        # Really ISnapBuild, patched in _schema_circular_imports.py.
        value_type=Reference(schema=Interface), readonly=True)))

    pending_builds = exported(doNotSnapshot(CollectionField(
        title=_("Pending builds of this snap package."),
        description=_(
            "Pending builds of this snap package, sorted in descending "
            "order of creation."),
        # Really ISnapBuild, patched in _schema_circular_imports.py.
        value_type=Reference(schema=Interface), readonly=True)))


class ISnapEdit(Interface):
    """`ISnap` methods that require launchpad.Edit permission."""

    @export_destructor_operation()
    @operation_for_version("devel")
    def destroySelf():
        """Delete this snap package, provided that it has no builds."""


class ISnapEditableAttributes(IHasOwner):
    """`ISnap` attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """
    date_last_modified = exported(Datetime(
        title=_("Date last modified"), required=True, readonly=True))

    owner = exported(PersonChoice(
        title=_("Owner"), required=True, readonly=False,
        vocabulary="AllUserTeamsParticipationPlusSelf",
        description=_("The owner of this snap package.")))

    distro_series = exported(Reference(
        IDistroSeries, title=_("Distro Series"), required=True, readonly=False,
        description=_(
            "The series for which the snap package should be built.")))

    name = exported(TextLine(
        title=_("Name"), required=True, readonly=False,
        constraint=name_validator,
        description=_("The name of the snap package.")))

    description = exported(Text(
        title=_("Description"), required=False, readonly=False,
        description=_("A description of the snap package.")))

    branch = exported(ReferenceChoice(
        title=_("Bazaar branch"), schema=IBranch, vocabulary="Branch",
        required=False, readonly=False,
        description=_(
            "A Bazaar branch containing a snapcraft.yaml recipe at the top "
            "level.")))

    git_repository = exported(ReferenceChoice(
        title=_("Git repository"),
        schema=IGitRepository, vocabulary="GitRepository",
        required=False, readonly=False,
        description=_(
            "A Git repository with a branch containing a snapcraft.yaml "
            "recipe at the top level.")))

    git_path = exported(TextLine(
        title=_("Git branch path"), required=False, readonly=False,
        description=_(
            "The path of the Git branch containing a snapcraft.yaml recipe at "
            "the top level.")))


class ISnapAdminAttributes(Interface):
    """`ISnap` attributes that can be edited by admins.

    These attributes need launchpad.View to see, and launchpad.Admin to change.
    """
    require_virtualized = exported(Bool(
        title=_("Require virtualized builders"), required=True, readonly=False,
        description=_("Only build this snap package on virtual builders.")))

    processors = exported(CollectionField(
        title=_("Processors"),
        description=_(
            "The architectures for which the snap package should be built."),
        value_type=Reference(schema=IProcessor),
        readonly=False))


class ISnapAdmin(Interface):
    """`ISnap` methods that require launchpad.Admin permission."""

    @operation_parameters(
        processors=List(
            value_type=Reference(schema=IProcessor), required=True))
    @export_write_operation()
    @operation_for_version("devel")
    def setProcessors(processors):
        """Set the architectures for which the snap package should be built."""


class ISnap(
    ISnapView, ISnapEdit, ISnapEditableAttributes, ISnapAdminAttributes,
    ISnapAdmin):
    """A buildable snap package."""

    # XXX cjwatson 2015-07-17 bug=760849: "beta" is a lie to get WADL
    # generation working.  Individual attributes must set their version to
    # "devel".
    export_as_webservice_entry(as_of="beta")


class ISnapSet(Interface):
    """A utility to create and access snap packages."""

    export_as_webservice_collection(ISnap)

    @call_with(registrant=REQUEST_USER)
    @export_factory_operation(
        ISnap, [
            "owner", "distro_series", "name", "description", "branch",
            "git_repository", "git_path"])
    @operation_for_version("devel")
    def new(registrant, owner, distro_series, name, description=None,
            branch=None, git_repository=None, git_path=None,
            require_virtualized=True, processors=None, date_created=None):
        """Create an `ISnap`."""

    def exists(owner, name):
        """Check to see if a matching snap exists."""

    @operation_parameters(
        owner=Reference(IPerson, title=_("Owner"), required=True),
        name=TextLine(title=_("Snap name"), required=True))
    @operation_returns_entry(ISnap)
    @export_read_operation()
    @operation_for_version("devel")
    def getByName(owner, name):
        """Return the appropriate `ISnap` for the given objects."""

    def findByPerson(owner):
        """Return all snap packages with the given `owner`."""

    def findByBranch(branch):
        """Return all snap packages for the given Bazaar branch."""

    def findByGitRepository(repository):
        """Return all snap packages for the given Git repository."""

    def detachFromBranch(branch):
        """Detach all snap packages from the given Bazaar branch.

        After this, any snap packages that previously used this branch will
        have no source and so cannot dispatch new builds.
        """

    def detachFromGitRepository(repository):
        """Detach all snap packages from the given Git repository.

        After this, any snap packages that previously used this repository
        will have no source and so cannot dispatch new builds.
        """

    @collection_default_content()
    def empty_list():
        """Return an empty collection of snap packages.

        This only exists to keep lazr.restful happy.
        """