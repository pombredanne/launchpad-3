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

from lazr.restful.fields import (
    CollectionField,
    Reference,
    ReferenceChoice,
    )
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Datetime,
    Int,
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
from lp.registry.interfaces.role import IHasOwner
from lp.services.fields import (
    PersonChoice,
    PublicPersonChoice,
    )


SNAP_FEATURE_FLAG = u"snap.allow_new"


class SnapBuildAlreadyPending(Exception):
    """A build was requested when an identical build was already pending."""

    def __init__(self):
        super(SnapBuildAlreadyPending, self).__init__(
            "An identical build of this snap package is already pending.")


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


class SnapBuildDisallowedArchitecture(Exception):
    """A build was requested for a disallowed architecture."""

    def __init__(self, das):
        super(SnapBuildDisallowedArchitecture, self).__init__(
            "This snap package is not allowed to build for %s." %
            das.displayname)


class SnapFeatureDisabled(Unauthorized):
    """Only certain users can create new snap-related objects."""

    def __init__(self):
        super(SnapFeatureDisabled, self).__init__(
            "You do not have permission to create new snaps or new snap "
            "builds.")


class DuplicateSnapName(Exception):
    """Raised for snap packages with duplicate name/owner."""

    def __init__(self):
        super(DuplicateSnapName, self).__init__(
            "There is already a snap package with the same name and owner.")


class SnapNotOwner(Unauthorized):
    """The registrant/requester is not the owner or a member of its team."""


class NoSuchSnap(NameLookupFailed):
    """The requested snap package does not exist."""
    _message_prefix = "No such snap package with this owner"


class NoSourceForSnap(Exception):
    """Snap packages must have a source (Bazaar branch or Git repository)."""

    def __init__(self):
        super(NoSourceForSnap, self).__init__(
            "New snap packages must have either a Bazaar branch or a Git "
            "repository.")


class CannotDeleteSnap(Exception):
    """This snap package cannot be deleted."""


class ISnapView(Interface):
    """`ISnap` attributes that require launchpad.View permission."""

    id = Int(title=_("ID"), required=True, readonly=True)

    date_created = Datetime(
        title=_("Date created"), required=True, readonly=True)

    registrant = PublicPersonChoice(
        title=_("Registrant"), required=True, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person who registered this snap package."))

    def requestBuild(requester, archive, distro_arch_series, pocket):
        """Request that the snap package be built.

        :param requester: The person requesting the build.
        :param archive: The IArchive to associate the build with.
        :param distro_arch_series: The architecture to build for.
        :param pocket: The pocket that should be targeted.
        :return: `ISnapBuild`.
        """

    builds = Attribute("All builds of this snap package.")

    completed_builds = Attribute("Completed builds of this snap package.")

    pending_builds = Attribute("Pending builds of this snap package.")


class ISnapEdit(Interface):
    """`ISnap` methods that require launchpad.Edit permission."""

    def destroySelf():
        """Delete this snap package, provided that it has no builds."""


class ISnapEditableAttributes(IHasOwner):
    """`ISnap` attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """
    date_last_modified = Datetime(
        title=_("Date last modified"), required=True, readonly=True)

    owner = PersonChoice(
        title=_("Owner"), required=True, readonly=False,
        vocabulary="AllUserTeamsParticipationPlusSelf",
        description=_("The owner of this snap package."))

    distro_series = Reference(
        IDistroSeries, title=_("Distro Series"), required=True, readonly=False,
        description=_(
            "The series for which the snap package should be built."))

    name = TextLine(
        title=_("Name"), required=True, readonly=False,
        constraint=name_validator,
        description=_("The name of the snap package."))

    description = Text(
        title=_("Description"), required=False, readonly=False,
        description=_("A description of the snap package."))

    branch = ReferenceChoice(
        title=_("Bazaar branch"), schema=IBranch, vocabulary="Branch",
        required=False, readonly=False,
        description=_(
            "A Bazaar branch containing a snapcraft.yaml recipe at the top "
            "level."))

    git_repository = ReferenceChoice(
        title=_("Git repository"),
        schema=IGitRepository, vocabulary="GitRepository",
        required=False, readonly=False,
        description=_(
            "A Git repository with a branch containing a snapcraft.yaml "
            "recipe at the top level."))

    git_path = TextLine(
        title=_("Git branch path"), required=False, readonly=False,
        description=_(
            "The path of the Git branch containing a snapcraft.yaml recipe at "
            "the top level."))


class ISnapAdminAttributes(Interface):
    """`ISnap` attributes that can be edited by admins.

    These attributes need launchpad.View to see, and launchpad.Admin to change.
    """
    require_virtualized = Bool(
        title=_("Require virtualized builders"), required=True, readonly=False,
        description=_("Only build this snap package on virtual builders."))

    processors = CollectionField(
        title=_("Processors"),
        description=_(
            "The architectures for which the snap package should be built."),
        value_type=Reference(schema=IProcessor),
        readonly=False)


class ISnapAdmin(Interface):
    """`ISnap` methods that require launchpad.Admin permission."""

    def setProcessors(processors):
        """Set the architectures for which the snap package should be built."""


class ISnap(
    ISnapView, ISnapEdit, ISnapEditableAttributes, ISnapAdminAttributes,
    ISnapAdmin):
    """A buildable snap package."""


class ISnapSet(Interface):
    """A utility to create and access snap packages."""

    def new(registrant, owner, distro_series, name, description=None,
            branch=None, git_repository=None, git_path=None,
            require_virtualized=True, processors=None, date_created=None):
        """Create an `ISnap`."""

    def exists(owner, name):
        """Check to see if a matching snap exists."""

    def getByName(owner, name):
        """Return the appropriate `ISnap` for the given objects."""

    def findByPerson(owner):
        """Return all snap packages with the given `owner`."""

    def empty_list():
        """Return an empty collection of snap packages.

        This only exists to keep lazr.restful happy.
        """
