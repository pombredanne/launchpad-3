# Copyright 2014-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Live filesystem interfaces."""

__metaclass__ = type

__all__ = [
    'CannotDeleteLiveFS',
    'DuplicateLiveFSName',
    'ILiveFS',
    'ILiveFSEditableAttributes',
    'ILiveFSEditableAttributes',
    'ILiveFSSet',
    'ILiveFSView',
    'LIVEFS_FEATURE_FLAG',
    'LiveFSBuildAlreadyPending',
    'LiveFSBuildArchiveOwnerMismatch',
    'LiveFSFeatureDisabled',
    'LiveFSNotOwner',
    'NoSuchLiveFS',
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
    exported,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import Interface
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Dict,
    Int,
    TextLine,
    )
from zope.security.interfaces import (
    Forbidden,
    Unauthorized,
    )

from lp import _
from lp.app.errors import NameLookupFailed
from lp.app.validators.name import name_validator
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


LIVEFS_FEATURE_FLAG = u"soyuz.livefs.allow_new"


@error_status(httplib.BAD_REQUEST)
class LiveFSBuildAlreadyPending(Exception):
    """A build was requested when an identical build was already pending."""

    def __init__(self):
        super(LiveFSBuildAlreadyPending, self).__init__(
            "An identical build of this live filesystem image is already "
            "pending.")


@error_status(httplib.FORBIDDEN)
class LiveFSBuildArchiveOwnerMismatch(Forbidden):
    """Builds into private archives require that owners match.

    The LiveFS owner must have write permission on the archive, so that a
    malicious live filesystem build can't steal any secrets that its owner
    didn't already have access to.  Furthermore, we want to make sure that
    future changes to the team owning the LiveFS don't grant it
    retrospective access to information about a private archive.  For now,
    the simplest way to do this is to require that the owners match exactly.
    """

    def __init__(self):
        super(LiveFSBuildArchiveOwnerMismatch, self).__init__(
            "Live filesystem builds against private archives are only "
            "allowed if the live filesystem owner and the archive owner are "
            "equal.")


@error_status(httplib.UNAUTHORIZED)
class LiveFSFeatureDisabled(Unauthorized):
    """Only certain users can create new LiveFS-related objects."""

    def __init__(self):
        super(LiveFSFeatureDisabled, self).__init__(
            "You do not have permission to create new live filesystems or "
            "new live filesystem builds.")


@error_status(httplib.BAD_REQUEST)
class DuplicateLiveFSName(Exception):
    """Raised for live filesystems with duplicate name/owner/distroseries."""

    def __init__(self):
        super(DuplicateLiveFSName, self).__init__(
            "There is already a live filesystem with the same name, owner, "
            "and distroseries.")


@error_status(httplib.UNAUTHORIZED)
class LiveFSNotOwner(Unauthorized):
    """The registrant/requester is not the owner or a member of its team."""


class NoSuchLiveFS(NameLookupFailed):
    """The requested LiveFS does not exist."""
    _message_prefix = "No such live filesystem with this owner/distroseries"


@error_status(httplib.BAD_REQUEST)
class CannotDeleteLiveFS(Exception):
    """This live filesystem cannot be deleted."""


class ILiveFSView(Interface):
    """`ILiveFS` attributes that require launchpad.View permission."""

    id = exported(Int(title=_("ID"), required=True, readonly=True))

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    registrant = exported(PublicPersonChoice(
        title=_("Registrant"), required=True, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_(
            "The person who registered this live filesystem image.")))

    @call_with(requester=REQUEST_USER)
    @operation_parameters(
        archive=Reference(schema=IArchive),
        distro_arch_series=Reference(schema=IDistroArchSeries),
        pocket=Choice(vocabulary=PackagePublishingPocket),
        unique_key=TextLine(
            title=_("A unique key for this build, if required."),
            required=False),
        metadata_override=Dict(
            title=_("A dict of data about the image."),
            key_type=TextLine(), required=False),
        version=TextLine(title=_("A version string for this build.")))
    # Really ILiveFSBuild, patched in _schema_circular_imports.py.
    @export_factory_operation(Interface, [])
    @operation_for_version("devel")
    def requestBuild(requester, archive, distro_arch_series, pocket,
                     unique_key=None, metadata_override=None, version=None):
        """Request that the live filesystem be built.

        :param requester: The person requesting the build.
        :param archive: The IArchive to associate the build with.
        :param distro_arch_series: The architecture to build for.
        :param pocket: The pocket that should be targeted.
        :param unique_key: An optional unique key for this build; if set,
            this identifies a class of builds for this live filesystem.
        :param metadata_override: An optional JSON string with a dict of
            data about the image; this will be merged into the metadata dict
            for the live filesystem.
        :param version: A version string for this build; if not set, a
            version string will be generated from the date and time when the
            build was requested.
        :return: `ILiveFSBuild`.
        """

    builds = exported(doNotSnapshot(CollectionField(
        title=_("All builds of this live filesystem."),
        description=_(
            "All builds of this live filesystem, sorted in descending order "
            "of finishing (or starting if not completed successfully)."),
        # Really ILiveFSBuild, patched in _schema_circular_imports.py.
        value_type=Reference(schema=Interface), readonly=True)))

    completed_builds = exported(doNotSnapshot(CollectionField(
        title=_("Completed builds of this live filesystem."),
        description=_(
            "Completed builds of this live filesystem, sorted in descending "
            "order of finishing."),
        # Really ILiveFSBuild, patched in _schema_circular_imports.py.
        value_type=Reference(schema=Interface), readonly=True)))

    pending_builds = exported(doNotSnapshot(CollectionField(
        title=_("Pending builds of this live filesystem."),
        description=_(
            "Pending builds of this live filesystem, sorted in descending "
            "order of creation."),
        # Really ILiveFSBuild, patched in _schema_circular_imports.py.
        value_type=Reference(schema=Interface), readonly=True)))


class ILiveFSEdit(Interface):
    """`ILiveFS` methods that require launchpad.Edit permission."""

    @export_destructor_operation()
    @operation_for_version("devel")
    def destroySelf():
        """Delete this live filesystem, provided that it has no builds."""


class ILiveFSEditableAttributes(IHasOwner):
    """`ILiveFS` attributes that can be edited.

    These attributes need launchpad.View to see, and launchpad.Edit to change.
    """
    date_last_modified = exported(Datetime(
        title=_("Date last modified"), required=True, readonly=True))

    owner = exported(PersonChoice(
        title=_("Owner"), required=True, readonly=False,
        vocabulary="AllUserTeamsParticipationPlusSelf",
        description=_("The owner of this live filesystem image.")))

    distro_series = exported(Reference(
        IDistroSeries, title=_("Distro Series"), required=True, readonly=False,
        description=_("The series for which the image should be built.")))

    name = exported(TextLine(
        title=_("Name"), required=True, readonly=False,
        constraint=name_validator,
        description=_("The name of the live filesystem image.")))

    metadata = exported(Dict(
        title=_(
            "A dict of data about the image.  Entries here will be passed to "
            "the builder slave."),
        key_type=TextLine(), required=True, readonly=False))


class ILiveFSModerateAttributes(Interface):
    """Restricted `ILiveFS` attributes.

    These attributes need launchpad.View to see, and launchpad.Moderate to
    change.
    """
    relative_build_score = exported(Int(
        title=_("Relative build score"), required=True, readonly=False,
        description=_(
            "A delta to apply to all build scores for the live filesystem.  "
            "Builds with a higher score will build sooner.")))


class ILiveFSAdminAttributes(Interface):
    """`ILiveFS` attributes that can be edited by admins.

    These attributes need launchpad.View to see, and launchpad.Admin to change.
    """
    require_virtualized = exported(Bool(
        title=_("Require virtualized builders"), required=True, readonly=False,
        description=_(
            "Only build this live filesystem image on virtual builders.")))


class ILiveFS(
    ILiveFSView, ILiveFSEdit, ILiveFSEditableAttributes,
    ILiveFSModerateAttributes, ILiveFSAdminAttributes):
    """A buildable live filesystem image."""

    # XXX cjwatson 2014-05-06 bug=760849: "beta" is a lie to get WADL
    # generation working.  Individual attributes must set their version to
    # "devel".
    export_as_webservice_entry(
        singular_name="livefs", plural_name="livefses", as_of="beta")


class ILiveFSSet(Interface):
    """A utility to create and access live filesystems."""

    export_as_webservice_collection(ILiveFS)

    @call_with(registrant=REQUEST_USER)
    @export_factory_operation(
        ILiveFS, ["owner", "distro_series", "name", "metadata"])
    @operation_for_version("devel")
    def new(registrant, owner, distro_series, name, metadata,
            require_virtualized=True, date_created=None):
        """Create an `ILiveFS`."""

    def exists(owner, distro_series, name):
        """Check to see if a matching live filesystem exists."""

    @operation_parameters(
        owner=Reference(IPerson, title=_("Owner"), required=True),
        distro_series=Reference(
            IDistroSeries, title=_("Distroseries"), required=True),
        name=TextLine(title=_("Live filesystem name"), required=True))
    @operation_returns_entry(ILiveFS)
    @export_read_operation()
    @operation_for_version("devel")
    def getByName(owner, distro_series, name):
        """Return the appropriate `ILiveFS` for the given objects."""

    def interpret(owner_name, distribution_name, distro_series_name, name):
        """Like `getByName`, but takes names of objects."""

    def getByPerson(owner):
        """Return all live filesystems with the given `owner`."""

    @collection_default_content()
    def getAll():
        """Return all of the live filesystems in Launchpad.

        :return: A (potentially empty) sequence of `ILiveFS` instances.
        """
