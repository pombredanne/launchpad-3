# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Live filesystem interfaces."""

__metaclass__ = type

__all__ = [
    'DuplicateLiveFSName',
    'ILiveFS',
    'ILiveFSEditableAttributes',
    'ILiveFSSet',
    'ILiveFSView',
    'InvalidLiveFSNamespace',
    'LIVEFS_FEATURE_FLAG',
    'LiveFSBuildAlreadyPending',
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
    export_factory_operation,
    export_write_operation,
    exported,
    operation_for_version,
    operation_parameters,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import Interface
from zope.schema import (
    Choice,
    Datetime,
    Dict,
    Int,
    TextLine,
    )
from zope.security.interfaces import Unauthorized

from lp import _
from lp.app.errors import NameLookupFailed
from lp.app.validators.name import name_validator
from lp.registry.interfaces.distroseries import IDistroSeries
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


@error_status(httplib.UNAUTHORIZED)
class LiveFSFeatureDisabled(Unauthorized):
    """Only certain users can create new LiveFS-related objects."""

    def __init__(self):
        super(LiveFSFeatureDisabled, self).__init__(
            "You do not have permission to create new live filesystems or "
            "new live filesystem builds.")


class InvalidLiveFSNamespace(Exception):
    """Raised when someone tries to lookup a namespace with a bad name.

    By 'bad', we mean that the name is unparsable.  It might be too short,
    too long, or malformed in some other way.
    """

    def __init__(self, name):
        self.name = name
        super(InvalidLiveFSNamespace, self).__init__(
            "Cannot understand namespace name: '%s'" % name)


class NoSuchLiveFS(NameLookupFailed):
    """Raised when we try to load a live filesystem that does not exist."""

    _message_prefix = "No such live filesystem"


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
        distroarchseries=Reference(schema=IDistroArchSeries),
        pocket=Choice(vocabulary=PackagePublishingPocket),
        unique_key=TextLine(
            title=_("A unique key for this build, if required."),
            required=False),
        metadata_override=Dict(
            title=_("A JSON string with a dict of data about the image."),
            key_type=TextLine(), required=False))
    # Really ILiveFSBuild, patched in _schema_circular_imports.py.
    @export_factory_operation(Interface, [])
    @export_write_operation()
    @operation_for_version("devel")
    def requestBuild(requester, archive, distroarchseries, pocket,
                     unique_key=None, metadata_override=None):
        """Request that the live filesystem be built.

        :param requester: The person requesting the build.
        :param archive: The IArchive to associate the build with.
        :param distroarchseries: The architecture to build for.
        :param pocket: The pocket that should be targeted.
        :param unique_key: An optional unique key for this build; if set,
            this identifies a class of builds for this live filesystem.
        :param metadata_override: An optional JSON string with a dict of
            data about the image; this will be merged into the metadata dict
            for the live filesystem.
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

    distroseries = exported(Reference(
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


class ILiveFS(ILiveFSView, ILiveFSEditableAttributes):
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
        ILiveFS, ["owner", "distroseries", "name", "metadata"])
    @operation_for_version("devel")
    def new(registrant, owner, distroseries, name, metadata,
            date_created=None):
        """Create an `ILiveFS`."""

    def exists(owner, distroseries, name):
        """Check to see if a matching live filesystem exists."""

    def get(owner, distroseries, name):
        """Return the appropriate `ILiveFS` for the given objects."""

    def interpret(owner_name, distribution_name, distroseries_name, name):
        """Like `get`, but takes names of objects."""

    @collection_default_content()
    def getAll():
        """Return all of the live filesystems in Launchpad.

        :return: A (potentially empty) sequence of `ILiveFS` instances.
        """

    def traverse(segments):
        """Look up the `ILiveFS` at the path given by 'segments'.

        The iterable 'segments' will be consumed until a live filesystem is
        found.  As soon as a live filesystem is found, it will be returned
        and the consumption of segments will stop.  Thus, there will often
        be unconsumed segments that can be used for further traversal.

        :param segments: An iterable of names of Launchpad components.
            The first segment is the username, *not* preceded by a '~'.
        :raise InvalidNamespace: if there are not enough segments to define
            a live filesystem.
        :raise NoSuchPerson: if the person referred to cannot be found.
        :raise NoSuchDistribution: if the distribution referred to cannot be
            found.
        :raise NoSuchDistroSeries: if the distroseries referred to cannot be
            found.
        :raise NoSuchLiveFS: if the live filesystem referred to cannot be
            found.
        :return: `ILiveFS`.
        """
