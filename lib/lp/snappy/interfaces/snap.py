# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Snap package interfaces."""

__metaclass__ = type

__all__ = [
    'BadSnapSearchContext',
    'BadSnapSource',
    'CannotAuthorizeStoreUploads',
    'CannotModifySnapProcessor',
    'CannotRequestAutoBuilds',
    'DuplicateSnapName',
    'ISnap',
    'ISnapEdit',
    'ISnapSet',
    'ISnapView',
    'NoSourceForSnap',
    'NoSuchSnap',
    'SNAP_PRIVATE_FEATURE_FLAG',
    'SNAP_TESTING_FLAGS',
    'SNAP_WEBHOOKS_FEATURE_FLAG',
    'SnapAuthorizationBadMacaroon',
    'SnapBuildAlreadyPending',
    'SnapBuildArchiveOwnerMismatch',
    'SnapBuildDisallowedArchitecture',
    'SnapNotOwner',
    'SnapPrivacyMismatch',
    'SnapPrivateFeatureDisabled',
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
    operation_returns_collection_of,
    operation_returns_entry,
    REQUEST_USER,
    )
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
    Choice,
    Datetime,
    Dict,
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
from lp.app.interfaces.launchpad import IPrivacy
from lp.app.validators.name import name_validator
from lp.buildmaster.interfaces.processor import IProcessor
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.gitref import IGitRef
from lp.code.interfaces.gitrepository import IGitRepository
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.role import IHasOwner
from lp.services.fields import (
    PersonChoice,
    PublicPersonChoice,
    URIField,
    )
from lp.services.webhooks.interfaces import IWebhookTarget
from lp.snappy.interfaces.snappyseries import (
    ISnappyDistroSeries,
    ISnappySeries,
    )
from lp.snappy.validators.channels import channels_validator
from lp.soyuz.interfaces.archive import IArchive
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeries


SNAP_PRIVATE_FEATURE_FLAG = u"snap.allow_private"
SNAP_WEBHOOKS_FEATURE_FLAG = u"snap.webhooks.enabled"


SNAP_TESTING_FLAGS = {
    SNAP_PRIVATE_FEATURE_FLAG: u"on",
    SNAP_WEBHOOKS_FEATURE_FLAG: u"on",
    }


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
class SnapPrivateFeatureDisabled(Unauthorized):
    """Only certain users can create private snap objects."""

    def __init__(self):
        super(SnapPrivateFeatureDisabled, self).__init__(
            "You do not have permission to create private snaps")


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
    """Snap packages must have a source (Bazaar or Git branch)."""

    def __init__(self):
        super(NoSourceForSnap, self).__init__(
            "New snap packages must have either a Bazaar branch or a Git "
            "branch.")


@error_status(httplib.BAD_REQUEST)
class BadSnapSource(Exception):
    """The elements of the source for a snap package are inconsistent."""


@error_status(httplib.BAD_REQUEST)
class SnapPrivacyMismatch(Exception):
    """Snap package privacy does not match its content."""

    def __init__(self):
        super(SnapPrivacyMismatch, self).__init__(
            "Snap contains private information and cannot be public.")


class BadSnapSearchContext(Exception):
    """The context is not valid for a snap package search."""


@error_status(httplib.FORBIDDEN)
class CannotModifySnapProcessor(Exception):
    """Tried to enable or disable a restricted processor on an snap package."""

    _fmt = (
        '%(processor)s is restricted, and may only be enabled or disabled '
        'by administrators.')

    def __init__(self, processor):
        super(CannotModifySnapProcessor, self).__init__(
            self._fmt % {'processor': processor.name})


@error_status(httplib.BAD_REQUEST)
class CannotAuthorizeStoreUploads(Exception):
    """Cannot authorize uploads of a snap package to the store."""


@error_status(httplib.INTERNAL_SERVER_ERROR)
class SnapAuthorizationBadMacaroon(Exception):
    """The macaroon generated to authorize store uploads is unusable."""


@error_status(httplib.BAD_REQUEST)
class CannotRequestAutoBuilds(Exception):
    """Snap package is not configured for automatic builds."""

    def __init__(self, field):
        super(CannotRequestAutoBuilds, self).__init__(
            "This snap package cannot have automatic builds created for it "
            "because %s is not set." % field)


class ISnapView(Interface):
    """`ISnap` attributes that require launchpad.View permission."""

    id = Int(title=_("ID"), required=True, readonly=True)

    date_created = exported(Datetime(
        title=_("Date created"), required=True, readonly=True))

    registrant = exported(PublicPersonChoice(
        title=_("Registrant"), required=True, readonly=True,
        vocabulary="ValidPersonOrTeam",
        description=_("The person who registered this snap package.")))

    source = Attribute(
        "The source branch for this snap package (VCS-agnostic).")

    available_processors = Attribute(
        "The architectures that are available to be enabled or disabled for "
        "this snap package.")

    @call_with(check_permissions=True, user=REQUEST_USER)
    @operation_parameters(
        processors=List(
            value_type=Reference(schema=IProcessor), required=True))
    @export_write_operation()
    @operation_for_version("devel")
    def setProcessors(processors, check_permissions=False, user=None):
        """Set the architectures for which the snap package should be built."""

    def getAllowedArchitectures():
        """Return all distroarchseries that this package can build for.

        :return: Sequence of `IDistroArchSeries` instances.
        """

    can_upload_to_store = exported(Bool(
        title=_("Can upload to store"), required=True, readonly=True,
        description=_(
            "Whether everything is set up to allow uploading builds of this "
            "snap package to the store.")))

    @call_with(requester=REQUEST_USER)
    @operation_parameters(
        archive=Reference(schema=IArchive),
        distro_arch_series=Reference(schema=IDistroArchSeries),
        pocket=Choice(vocabulary=PackagePublishingPocket),
        channels=Dict(
            title=_("Source snap channels to use for this build."),
            description=_(
                "A dictionary mapping snap names to channels to use for this "
                "build.  Currently only 'core' and 'snapcraft' keys are "
                "supported."),
            key_type=TextLine(), required=False))
    # Really ISnapBuild, patched in lp.snappy.interfaces.webservice.
    @export_factory_operation(Interface, [])
    @operation_for_version("devel")
    def requestBuild(requester, archive, distro_arch_series, pocket,
                     channels=None):
        """Request that the snap package be built.

        :param requester: The person requesting the build.
        :param archive: The IArchive to associate the build with.
        :param distro_arch_series: The architecture to build for.
        :param pocket: The pocket that should be targeted.
        :param channels: A dictionary mapping snap names to channels to use
            for this build.
        :return: `ISnapBuild`.
        """

    @operation_parameters(
        snap_build_ids=List(
            title=_("A list of snap build ids."),
            value_type=Int()))
    @export_read_operation()
    @operation_for_version("devel")
    def getBuildSummariesForSnapBuildIds(snap_build_ids):
        """Return a dictionary containing a summary of the build statuses.

        :param snap_build_ids: A list of snap build ids.
        :type source_ids: ``list``
        :return: A dict consisting of the overall status summaries for the
            given snap builds.
        """

    builds = exported(doNotSnapshot(CollectionField(
        title=_("All builds of this snap package."),
        description=_(
            "All builds of this snap package, sorted in descending order "
            "of finishing (or starting if not completed successfully)."),
        # Really ISnapBuild, patched in lp.snappy.interfaces.webservice.
        value_type=Reference(schema=Interface), readonly=True)))

    completed_builds = exported(doNotSnapshot(CollectionField(
        title=_("Completed builds of this snap package."),
        description=_(
            "Completed builds of this snap package, sorted in descending "
            "order of finishing."),
        # Really ISnapBuild, patched in lp.snappy.interfaces.webservice.
        value_type=Reference(schema=Interface), readonly=True)))

    pending_builds = exported(doNotSnapshot(CollectionField(
        title=_("Pending builds of this snap package."),
        description=_(
            "Pending builds of this snap package, sorted in descending "
            "order of creation."),
        # Really ISnapBuild, patched in lp.snappy.interfaces.webservice.
        value_type=Reference(schema=Interface), readonly=True)))


class ISnapEdit(IWebhookTarget):
    """`ISnap` methods that require launchpad.Edit permission."""

    # Really ISnapBuild, patched in lp.snappy.interfaces.webservice.
    @operation_returns_collection_of(Interface)
    @export_write_operation()
    @operation_for_version("devel")
    def requestAutoBuilds(allow_failures=False, logger=None):
        """Create and return automatic builds for this snap package.

        :param allow_failures: If True, log exceptions other than "already
            pending" from individual build requests; if False, raise them to
            the caller.
        :param logger: An optional logger.
        :raises CannotRequestAutoBuilds: if no auto_build_archive or
            auto_build_pocket is set.
        :return: A sequence of `ISnapBuild` instances.
        """

    @export_write_operation()
    @operation_for_version("devel")
    def beginAuthorization():
        """Begin authorizing uploads of this snap package to the store.

        This is intended for use by third-party sites integrating with
        Launchpad.  Most users should visit <snap URL>/+authorize instead.

        :param success_url: The URL to redirect to when authorization is
            complete.  If None (only allowed for internal use), defaults to
            the canonical URL of the snap.
        :raises CannotAuthorizeStoreUploads: if the snap package is not
            properly configured for store uploads.
        :raises BadRequestPackageUploadResponse: if the store returns an
            error or a response without a macaroon when asked to issue a
            package_upload macaroon.
        :raises SnapAuthorizationBadMacaroon: if the package_upload macaroon
            returned by the store has unsuitable SSO caveats.
        :return: The SSO caveat ID from the package_upload macaroon returned
            by the store.  The third-party site should acquire a discharge
            macaroon for this caveat using OpenID and then call
            `completeAuthorization`.
        """

    @operation_parameters(
        root_macaroon=TextLine(
            title=_("Serialized root macaroon"),
            description=_(
                "Only required if not already set by beginAuthorization."),
            required=False),
        discharge_macaroon=TextLine(
            title=_("Serialized discharge macaroon"),
            description=_(
                "Only required if root macaroon has SSO third-party caveat."),
            required=False))
    @export_write_operation()
    @operation_for_version("devel")
    def completeAuthorization(root_macaroon=None, discharge_macaroon=None):
        """Complete authorizing uploads of this snap package to the store.

        This is intended for use by third-party sites integrating with
        Launchpad.

        :param root_macaroon: A serialized root macaroon returned by the
            store.  Only required if not already set by beginAuthorization.
        :param discharge_macaroon: The serialized discharge macaroon
            returned by SSO via OpenID.  Only required if the root macaroon
            has a third-party caveat addressed to SSO.
        :raises CannotAuthorizeStoreUploads: if the snap package is not
            properly configured for store uploads.
        """

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
            "A Bazaar branch containing a snap/snapcraft.yaml, "
            "snapcraft.yaml, or .snapcraft.yaml recipe at the top level.")))

    git_repository = exported(ReferenceChoice(
        title=_("Git repository"),
        schema=IGitRepository, vocabulary="GitRepository",
        required=False, readonly=True,
        description=_(
            "A Git repository with a branch containing a snap/snapcraft.yaml, "
            "snapcraft.yaml, or .snapcraft.yaml recipe at the top level.")))

    git_repository_url = exported(URIField(
        title=_("Git repository URL"), required=False, readonly=True,
        description=_(
            "The URL of a Git repository with a branch containing a "
            "snap/snapcraft.yaml, snapcraft.yaml, or .snapcraft.yaml recipe "
            "at the top level."),
        allowed_schemes=["git", "http", "https"],
        allow_userinfo=True,
        allow_port=True,
        allow_query=False,
        allow_fragment=False,
        trailing_slash=False))

    git_path = TextLine(
        title=_("Git branch path"), required=False, readonly=False,
        description=_(
            "The path of the Git branch containing a snap/snapcraft.yaml, "
            "snapcraft.yaml, or .snapcraft.yaml recipe at the top level."))
    _api_git_path = exported(
        TextLine(
            title=_("Git branch path"), required=False, readonly=False,
            description=_(
                "The path of the Git branch containing a snap/snapcraft.yaml, "
                "snapcraft.yaml, or .snapcraft.yaml recipe at the top "
                "level.")),
        exported_as="git_path")

    git_ref = exported(Reference(
        IGitRef, title=_("Git branch"), required=False, readonly=False,
        description=_(
            "The Git branch containing a snap/snapcraft.yaml, snapcraft.yaml, "
            "or .snapcraft.yaml recipe at the top level.")))

    auto_build = exported(Bool(
        title=_("Automatically build when branch changes"),
        required=True, readonly=False,
        description=_(
            "Whether this snap package is built automatically when the branch "
            "containing its snap/snapcraft.yaml, snapcraft.yaml, or "
            ".snapcraft.yaml recipe changes.")))

    auto_build_archive = exported(Reference(
        IArchive, title=_("Source archive for automatic builds"),
        required=False, readonly=False,
        description=_(
            "The archive from which automatic builds of this snap package "
            "should be built.")))

    auto_build_pocket = exported(Choice(
        title=_("Pocket for automatic builds"),
        vocabulary=PackagePublishingPocket, required=False, readonly=False,
        description=_(
            "The package stream within the source distribution series to use "
            "when building the snap package.")))

    auto_build_channels = exported(Dict(
        title=_("Source snap channels for automatic builds"),
        key_type=TextLine(), required=False, readonly=False,
        description=_(
            "A dictionary mapping snap names to channels to use when building "
            "this snap package.  Currently only 'core' and 'snapcraft' keys "
            "are supported.")))

    is_stale = Bool(
        title=_("Snap package is stale and is due to be rebuilt."),
        required=True, readonly=False)

    store_upload = exported(Bool(
        title=_("Automatically upload to store"),
        required=True, readonly=False,
        description=_(
            "Whether builds of this snap package are automatically uploaded "
            "to the store.")))

    # XXX cjwatson 2016-12-08: We should limit this to series that are
    # compatible with distro_series, but that entails validating the case
    # where both are changed in a single PATCH request in such a way that
    # neither is compatible with the old value of the other.  As far as I
    # can tell lazr.restful only supports per-field validation.
    store_series = exported(ReferenceChoice(
        title=_("Store series"),
        schema=ISnappySeries, vocabulary="SnappySeries",
        required=False, readonly=False,
        description=_(
            "The series in which this snap package should be published in the "
            "store.")))

    store_distro_series = ReferenceChoice(
        title=_("Store and distro series"),
        schema=ISnappyDistroSeries, vocabulary="SnappyDistroSeries",
        required=False, readonly=False)

    store_name = exported(TextLine(
        title=_("Registered store package name"),
        required=False, readonly=False,
        description=_(
            "The registered name of this snap package in the store.")))

    store_secrets = List(
        value_type=TextLine(), title=_("Store upload tokens"),
        required=False, readonly=False,
        description=_(
            "Serialized secrets issued by the store and the login service to "
            "authorize uploads of this snap package."))

    store_channels = exported(List(
        title=_("Store channels"),
        required=False, readonly=False, constraint=channels_validator,
        description=_(
            "Channels to release this snap package to after uploading it to "
            "the store. A channel is defined by a combination of an optional "
            " track and a risk, e.g. '2.1/stable', or 'stable'.")))


class ISnapAdminAttributes(Interface):
    """`ISnap` attributes that can be edited by admins.

    These attributes need launchpad.View to see, and launchpad.Admin to change.
    """

    private = exported(Bool(
        title=_("Private"), required=False, readonly=False,
        description=_("Whether or not this snap is private.")))

    require_virtualized = exported(Bool(
        title=_("Require virtualized builders"), required=True, readonly=False,
        description=_("Only build this snap package on virtual builders.")))

    processors = exported(CollectionField(
        title=_("Processors"),
        description=_(
            "The architectures for which the snap package should be built."),
        value_type=Reference(schema=IProcessor),
        readonly=False))

    allow_internet = exported(Bool(
        title=_("Allow external network access"),
        required=True, readonly=False,
        description=_(
            "Allow access to external network resources via a proxy.  "
            "Resources hosted on Launchpad itself are always allowed.")))


class ISnap(
    ISnapView, ISnapEdit, ISnapEditableAttributes, ISnapAdminAttributes,
    IPrivacy):
    """A buildable snap package."""

    # XXX cjwatson 2015-07-17 bug=760849: "beta" is a lie to get WADL
    # generation working.  Individual attributes must set their version to
    # "devel".
    export_as_webservice_entry(as_of="beta")


class ISnapSet(Interface):
    """A utility to create and access snap packages."""

    export_as_webservice_collection(ISnap)

    @call_with(registrant=REQUEST_USER)
    @operation_parameters(
        processors=List(
            value_type=Reference(schema=IProcessor), required=False))
    @export_factory_operation(
        ISnap, [
            "owner", "distro_series", "name", "description", "branch",
            "git_repository", "git_repository_url", "git_path", "git_ref",
            "auto_build", "auto_build_archive", "auto_build_pocket",
            "private", "store_upload", "store_series", "store_name",
            "store_channels"])
    @operation_for_version("devel")
    def new(registrant, owner, distro_series, name, description=None,
            branch=None, git_repository=None, git_repository_url=None,
            git_path=None, git_ref=None, auto_build=False,
            auto_build_archive=None, auto_build_pocket=None,
            require_virtualized=True, processors=None, date_created=None,
            private=False, store_upload=False, store_series=None,
            store_name=None, store_secrets=None, store_channels=None):
        """Create an `ISnap`."""

    def exists(owner, name):
        """Check to see if a matching snap exists."""

    def isValidPrivacy(private, owner, branch=None, git_ref=None):
        """Whether or not the privacy context is valid."""

    @operation_parameters(
        owner=Reference(IPerson, title=_("Owner"), required=True),
        name=TextLine(title=_("Snap name"), required=True))
    @operation_returns_entry(ISnap)
    @export_read_operation()
    @operation_for_version("devel")
    def getByName(owner, name):
        """Return the appropriate `ISnap` for the given objects."""

    @operation_parameters(
        owner=Reference(IPerson, title=_("Owner"), required=True))
    @operation_returns_collection_of(ISnap)
    @export_read_operation()
    @operation_for_version("devel")
    def findByOwner(owner):
        """Return all snap packages with the given `owner`."""

    def findByPerson(person, visible_by_user=None):
        """Return all snap packages relevant to `person`.

        This returns snap packages for Bazaar or Git branches owned by
        `person`, or where `person` is the owner of the snap package.

        :param person: An `IPerson`.
        :param visible_by_user: If not None, only return packages visible by
            this user; otherwise, only return publicly-visible packages.
        """

    def findByProject(project, visible_by_user=None):
        """Return all snap packages for the given project.

        :param project: An `IProduct`.
        :param visible_by_user: If not None, only return packages visible by
            this user; otherwise, only return publicly-visible packages.
        """

    def findByBranch(branch):
        """Return all snap packages for the given Bazaar branch."""

    def findByGitRepository(repository, paths=None):
        """Return all snap packages for the given Git repository.

        :param repository: An `IGitRepository`.
        :param paths: If not None, only return snap packages for one of
            these Git reference paths.
        """

    def findByGitRef(ref):
        """Return all snap packages for the given Git reference."""

    def findByContext(context, visible_by_user=None, order_by_date=True):
        """Return all snap packages for the given context.

        :param context: An `IPerson`, `IProduct, `IBranch`,
            `IGitRepository`, or `IGitRef`.
        :param visible_by_user: If not None, only return packages visible by
            this user; otherwise, only return publicly-visible packages.
        :param order_by_date: If True, order packages by descending
            modification date.
        :raises BadSnapSearchContext: if the context is not understood.
        """

    @operation_parameters(
        url=TextLine(title=_("The URL to search for.")),
        owner=Reference(IPerson, title=_("Owner"), required=False))
    @call_with(visible_by_user=REQUEST_USER)
    @operation_returns_collection_of(ISnap)
    @export_read_operation()
    @operation_for_version("devel")
    def findByURL(url, owner=None, visible_by_user=None):
        """Return all snap packages that build from the given URL.

        This currently only works for packages that build directly from a
        URL, rather than being linked to a Bazaar branch or Git repository
        hosted in Launchpad.

        :param url: A URL.
        :param owner: Only return packages owned by this user.
        :param visible_by_user: If not None, only return packages visible by
            this user; otherwise, only return publicly-visible packages.
        """

    @operation_parameters(
        url_prefix=TextLine(title=_("The URL prefix to search for.")),
        owner=Reference(IPerson, title=_("Owner"), required=False))
    @call_with(visible_by_user=REQUEST_USER)
    @operation_returns_collection_of(ISnap)
    @export_read_operation()
    @operation_for_version("devel")
    def findByURLPrefix(url_prefix, owner=None, visible_by_user=None):
        """Return all snap packages that build from a URL with this prefix.

        This currently only works for packages that build directly from a
        URL, rather than being linked to a Bazaar branch or Git repository
        hosted in Launchpad.

        :param url_prefix: A URL prefix.
        :param owner: Only return packages owned by this user.
        :param visible_by_user: If not None, only return packages visible by
            this user; otherwise, only return publicly-visible packages.
        """

    @operation_parameters(
        url_prefixes=List(
            title=_("The URL prefixes to search for."), value_type=TextLine()),
        owner=Reference(IPerson, title=_("Owner"), required=False))
    @call_with(visible_by_user=REQUEST_USER)
    @operation_returns_collection_of(ISnap)
    @export_read_operation()
    @operation_for_version("devel")
    def findByURLPrefixes(url_prefixes, owner=None, visible_by_user=None):
        """Return all snap packages that build from a URL with any of these
        prefixes.

        This currently only works for packages that build directly from a
        URL, rather than being linked to a Bazaar branch or Git repository
        hosted in Launchpad.

        :param url_prefixes: A list of URL prefixes.
        :param owner: Only return packages owned by this user.
        :param visible_by_user: If not None, only return packages visible by
            this user; otherwise, only return publicly-visible packages.
        """

    def preloadDataForSnaps(snaps, user):
        """Load the data related to a list of snap packages."""

    def makeAutoBuilds(logger=None):
        """Create and return automatic builds for stale snap packages.

        :param logger: An optional logger.
        """

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
