# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces including and related to IDistribution."""

__metaclass__ = type

__all__ = [
    'IDistribution',
    'IDistributionEditRestricted',
    'IDistributionMirrorMenuMarker',
    'IDistributionPublic',
    'IDistributionSet',
    'NoSuchDistribution',
    ]

from zope.schema import Bool, Choice, Datetime, Text, TextLine
from zope.interface import Attribute, Interface

from lazr.restful.fields import CollectionField, Reference
from lazr.restful.interface import copy_field
from lazr.restful.declarations import (
   collection_default_content, export_as_webservice_collection,
   export_as_webservice_entry, export_operation_as,
   export_read_operation, exported, operation_parameters,
   operation_returns_collection_of, operation_returns_entry,
   rename_parameters_as)

from canonical.launchpad import _
from canonical.launchpad.fields import (
    Description, PublicPersonChoice, Summary, Title)
from lp.registry.interfaces.announcement import IMakesAnnouncements
from canonical.launchpad.interfaces.bugtarget import (
    IBugTarget, IOfficialBugTagTargetPublic, IOfficialBugTagTargetRestricted)
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords
from lp.registry.interfaces.karma import IKarmaContext
from canonical.launchpad.interfaces.launchpad import (
    IHasAppointedDriver, IHasDrivers, IHasOwner, IHasSecurityContact,
    ILaunchpadUsage)
from lp.registry.interfaces.mentoringoffer import IHasMentoringOffers
from canonical.launchpad.interfaces.message import IMessage
from lp.registry.interfaces.milestone import (
    ICanGetMilestonesDirectly, IHasMilestones)
from lp.registry.interfaces.pillar import IPillar
from canonical.launchpad.interfaces.specificationtarget import (
    ISpecificationTarget)
from canonical.launchpad.interfaces.sprint import IHasSprints
from canonical.launchpad.interfaces.translationgroup import (
    IHasTranslationGroup)
from canonical.launchpad.webapp.interfaces import NameLookupFailed
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.fields import (
    IconImageUpload, LogoImageUpload, MugshotImageUpload, PillarNameField)



class IDistributionMirrorMenuMarker(Interface):
    """Marker interface for Mirror navigation."""


class DistributionNameField(PillarNameField):
    """The pillar for a distribution."""
    @property
    def _content_iface(self):
        """Return the interface of this pillar object."""
        return IDistribution


class IDistributionEditRestricted(IOfficialBugTagTargetRestricted):
    """IDistribution properties requiring launchpad.Edit permission."""

    def newSeries(name, displayname, title, summary, description,
                  version, parent_series, owner):
        """Creates a new distroseries."""


class IDistributionPublic(
    IBugTarget, ICanGetMilestonesDirectly, IHasAppointedDriver,
    IHasBuildRecords, IHasDrivers, IHasMentoringOffers, IHasMilestones,
    IHasOwner, IHasSecurityContact, IHasSprints, IHasTranslationGroup,
    IKarmaContext, ILaunchpadUsage, IMakesAnnouncements,
    IOfficialBugTagTargetPublic, IPillar, ISpecificationTarget):
    """Public IDistribution properties."""

    id = Attribute("The distro's unique number.")
    name = exported(
        DistributionNameField(
            title=_("Name"),
            constraint=name_validator,
            description=_("The distro's name."), required=True))
    displayname = exported(
        TextLine(
            title=_("Display Name"),
            description=_("The displayable name of the distribution."),
            required=True),
        exported_as='display_name')
    title = exported(
        Title(
            title=_("Title"),
            description=_("The distro's title."), required=True))
    summary = exported(
        Summary(
            title=_("Summary"),
            description=_(
                "The distribution summary. A short paragraph "
                "describing the goals and highlights of the distro."),
            required=True))
    homepage_content = exported(
        Text(
            title=_("Homepage Content"), required=False,
            description=_(
                "The content of this distribution's home page. Edit this and "
                "it will be displayed for all the world to see. It is NOT a "
                "wiki so you cannot undo changes.")))
    icon = exported(
        IconImageUpload(
            title=_("Icon"), required=False,
            default_image_resource='/@@/distribution',
            description=_(
                "A small image of exactly 14x14 pixels and at most 5kb in "
                "size, that can be used to identify this distribution. The "
                "icon will be displayed everywhere we list the distribution "
                "and link to it.")))
    logo = exported(
        LogoImageUpload(
            title=_("Logo"), required=False,
            default_image_resource='/@@/distribution-logo',
            description=_(
                "An image of exactly 64x64 pixels that will be displayed in "
                "the heading of all pages related to this distribution. It "
                "should be no bigger than 50kb in size.")))
    mugshot = exported(
        MugshotImageUpload(
            title=_("Brand"), required=False,
            default_image_resource='/@@/distribution-mugshot',
            description=_(
                "A large image of exactly 192x192 pixels, that will be "
                "displayed on this distribution's home page in Launchpad. "
                "It should be no bigger than 100kb in size. ")))
    description = exported(
        Description(
            title=_("Description"),
            description=_("The distro's description."),
            required=True))
    domainname = exported(
        TextLine(
            title=_("Domain name"),
            description=_("The distro's domain name."), required=True),
        exported_as='domain_name')
    owner = exported(
        PublicPersonChoice(
            title=_("Owner"), vocabulary='ValidOwner',
            description=_("The distro's owner."), required=True))
    date_created = exported(
        Datetime(title=_('Date created'),
                 description=_("The date this distribution was registered.")),
        exported_as='date_created')
    driver = exported(
        PublicPersonChoice(
            title=_("Driver"),
            description=_(
                "The person or team responsible for decisions about features "
                "and bugs that will be targeted for any series in this "
                "distribution. Note that you can also specify a driver "
                "on each series who's permissions will be limited to that "
                "specific series."),
            required=False, vocabulary='ValidPersonOrTeam'))
    drivers = Attribute(
        "Presents the distro driver as a list for consistency with "
        "IProduct.drivers where the list might include a project driver.")
    members = PublicPersonChoice(
        title=_("Members"),
        description=_("The distro's members team."), required=True,
        vocabulary='ValidPersonOrTeam')
    mirror_admin = PublicPersonChoice(
        title=_("Mirror Administrator"),
        description=_("The person or team that has the rights to administer "
                      "this distribution's mirrors"),
        required=True, vocabulary='ValidPersonOrTeam')
    lucilleconfig = TextLine(
        title=_("Lucille Config"),
        description=_("The Lucille Config."), required=False)
    archive_mirrors = Attribute(
        "All enabled and official ARCHIVE mirrors of this Distribution.")
    cdimage_mirrors = Attribute(
        "All enabled and official RELEASE mirrors of this Distribution.")
    disabled_mirrors = Attribute(
        "All disabled and official mirrors of this Distribution.")
    unofficial_mirrors = Attribute(
        "All unofficial mirrors of this Distribution.")
    pending_review_mirrors = Attribute(
        "All mirrors of this Distribution that haven't been reviewed yet.")
    serieses = exported(
        CollectionField(
            title=_("DistroSeries inside this Distribution"),
            # Really IDistroSeries, see below.
            value_type=Reference(schema=Interface)),
        exported_as="series")
    bounties = Attribute(_("The bounties that are related to this distro."))
    bugCounter = Attribute("The distro bug counter")
    is_read_only = Attribute(
        "True if this distro is just monitored by Launchpad, rather than "
        "allowing you to use Launchpad to actually modify the distro.")
    uploaders = Attribute(_(
        "ArchivePermission records for uploaders with rights to upload to "
        "this distribution."))

    # properties
    currentseries = exported(
        Reference(
            Interface, # Really IDistroSeries, see below
            title=_("Current series"),
            description=_(
                "The current development series of this distribution. "
                "Note that all maintainerships refer to the current "
                "series. When people ask about the state of packages "
                "in the distribution, we should interpret that query "
                "in the context of the currentseries.")),
        exported_as="current_series")

    full_functionality = Attribute(
        "Whether or not we enable the full functionality of Launchpad for "
        "this distribution. Currently only Ubuntu and some derivatives "
        "get the full functionality of LP")

    translation_focus = Choice(
        title=_("Translation Focus"),
        description=_(
            "The DistroSeries that should get the translation effort focus."),
        required=False,
        vocabulary='FilteredDistroSeries')

    language_pack_admin = Choice(
        title=_("Language Pack Administrator"),
        description=_("The distribution language pack administrator."),
        required=False, vocabulary='ValidPersonOrTeam')

    main_archive = exported(
        Reference(
            title=_('Distribution Main Archive.'), readonly=True,
            schema=Interface)) # Really IArchive, circular import fix below.

    all_distro_archives = exported(
        CollectionField(
            title=_("A sequence of the distribution's non-PPA Archives."),
            readonly=True, required=False,
            value_type=Reference(schema=Interface)),
                # Really Iarchive, circular import fix below.
        exported_as='archives')

    all_distro_archive_ids = Attribute(
        "A list containing the IDs of all the non-PPA archives.")

    upstream_report_excluded_packages = Attribute(
        "A list of the source packages that should not be shown on the "
        "upstream bug report for this Distribution.")

    has_published_binaries = Bool(
        title=_("Has Published Binaries"),
        description=_("True if this distribution has binaries published "
                      "on disk."),
        readonly=True, required=False)

    def getArchiveIDList(archive=None):
        """Return a list of archive IDs suitable for sqlvalues() or quote().

        If the archive param is supplied, just its ID will be returned in
        a list of one item.  If it is not supplied, return a list of
        all the IDs for all the archives for the distribution.
        """

    def __getitem__(name):
        """Returns a DistroSeries that matches name, or raises and
        exception if none exists."""

    def __iter__():
        """Iterate over the series for this distribution."""

    # Really IDistroSeries, see below
    @operation_returns_collection_of(Interface)
    @export_operation_as(name="getDevelopmentSeries")
    @export_read_operation()
    def getDevelopmentSerieses():
        """Return the DistroSerieses which are marked as in development."""

    @operation_parameters(
        name_or_version=TextLine(title=_("Name or version"), required=True))
    @operation_returns_entry(Interface) # Really IDistroSeries, see below
    @export_read_operation()
    def getSeries(name_or_version):
        """Return the series with the name or version given."""

    def getMirrorByName(name):
        """Return the mirror with the given name for this distribution or None
        if it's not found.
        """

    def newMirror(owner, speed, country, content, displayname=None,
                  description=None, http_base_url=None, ftp_base_url=None,
                  rsync_base_url=None, enabled=False,
                  official_candidate=False):
        """Create a new DistributionMirror for this distribution.

        At least one of http_base_url or ftp_base_url must be provided in
        order to create a mirror.
        """

    @operation_parameters(
        name=TextLine(title=_("Package name"), required=True))
    # Really returns IDistributionSourcePackage, see below.
    @operation_returns_entry(Interface)
    @export_read_operation()
    def getSourcePackage(name):
        """Return a DistributionSourcePackage with the given name for this
        distribution, or None.
        """

    def getSourcePackageRelease(sourcepackagerelease):
        """Returns an IDistributionSourcePackageRelease

        Receives a sourcepackagerelease.
        """

    def getCurrentSourceReleases(source_package_names):
        """Get the current release of a list of source packages.

        :param source_package_names: a list of `ISourcePackageName`
            instances.

        :return: a dict where the key is a `IDistributionSourcePackage`
            and the value is a `IDistributionSourcePackageRelease`.
        """

    def ensureRelatedBounty(bounty):
        """Ensure that the bounty is linked to this distribution. Return
        None.
        """

    def getDistroSeriesAndPocket(distroseriesname):
        """Return a (distroseries,pocket) tuple which is the given textual
        distroseriesname in this distribution."""

    def getSourcePackageCaches(archive=None):
        """The set of all source package info caches for this distribution.

        If 'archive' is not given it will return all caches stored for the
        distribution main archives (PRIMARY and PARTNER).
        """

    def removeOldCacheItems(archive, log):
        """Delete any cache records for removed packages."""

    def updateCompleteSourcePackageCache(archive, log, ztm, commit_chunk=500):
        """Update the source package cache.

        Consider every non-REMOVED sourcepackage.

        :param archive: target `IArchive`;
        :param log: logger object for printing debug level information;
        :param ztm:  transaction used for partial commits, every chunk of
            'commit_chunk' updates is committed;
        :param commit_chunk: number of updates before commit, defaults to 500.

        :return the number packages updated done
        """

    def updateSourcePackageCache(sourcepackagename, archive, log):
        """Update cached source package details.

        Update cache details for a given ISourcePackageName, including
        generated binarypackage names, summary and description fti.
        'log' is required and only prints debug level information.
        """

    @rename_parameters_as(text="source_match")
    @operation_parameters(
        text=TextLine(title=_("Source package name substring match"),
                      required=True))
    # Really returns IDistributionSourcePackage, see below.
    @operation_returns_collection_of(Interface)
    @export_read_operation()
    def searchSourcePackages(text):
        """Search for source packages that correspond to the given text.
        Returns a list of DistributionSourcePackage objects, in order of
        matching.
        """

    def searchBinaryPackages(package_name, exact_match=False):
        """Search for binary packages in this distribution.

        :param package_name: The binary package name to match.
        :param exact_match: If False, substring matches are done on the
            binary package names; if True only a full string match is
            returned.
        :return: A result set containing appropriate DistributionSourcePackage
            objects for the matching source.

        The returned results will consist of source packages that match
        (a substring of) their binary package names.
        """

    def searchBinaryPackagesFTI(package_name):
        """Do an FTI search on binary packages.

        :param package_name: The binary package name to search for.
        :return: A result set containing DistributionSourcePackageCache
            objects for the matching binaries found via an FTI search on
            DistroSeriesPackageCache.
        """

    def getFileByName(filename, archive=None, source=True, binary=True):
        """Find and return a LibraryFileAlias for the filename supplied.

        The file returned will be one of those published in the distribution.

        If searching both source and binary, and the file is found in the
        binary packages it'll return that over a file for a source package.

        If 'archive' is not passed the distribution.main_archive is assumed.

        At least one of source and binary must be true.

        Raises NotFoundError if it fails to find the named file.
        """

    def guessPackageNames(pkgname):
        """Try and locate source and binary package name objects that
        are related to the provided name --  which could be either a
        source or a binary package name. Returns a tuple of
        (sourcepackagename, binarypackagename) based on the current
        publishing status of these binary / source packages. Raises
        NotFoundError if it fails to find any package published with
        that name in the distribution.
        """

    def getAllPPAs():
        """Return all PPAs for this distribution."""

    def searchPPAs(text=None, show_inactive=False):
        """Return all PPAs matching the given text in this distribution.

        'text', when passed, will restrict results to Archives with matching
        description (using substring) or matching Archive.owner (using
        available person fti/ftq).

        'show_inactive', when False, will restrict results to Archive with
        at least one source publication in PENDING or PUBLISHED status.
        """

    def getPendingAcceptancePPAs():
        """Return only pending acceptance PPAs in this distribution."""

    def getPendingPublicationPPAs():
        """Return all PPAs in this distribution that are pending publication.

        A PPA is said to be pending publication if it has publishing records
        in the pending state or if it had packages deleted from it.
        """

    def getArchiveByComponent(component_name):
        """Return the archive most appropriate for the component name.

        Where different components may imply a different archive (e.g.
        partner), this method will return the archive for that component.

        If the component_name supplied is unknown, None is returned.
        """

    def getPackagesAndPublicUpstreamBugCounts(limit=50,
                                              exclude_packages=None):
        """Return list of tuples of packages, upstreams and public bug counts.

        :param limit: The maximum number of rows to return.
        :param exclude_packages: A list of source packages to exclude.
            These should be specified as strings which correspond with
            SourcePackageName.name.
        :returns: [(IDistroSourcePackage, IProduct, int, int, int, int), ...]

        This API is quite specialized; it returns a list of up to limit
        tuples containing IProducts and three different bug counts:
            - open bugs
            - triaged bugs
            - open bugs with an upstream task
            - open bugs with upstream tasks that are either linked to
              bug watches or to products that use_malone.
        """

    def getCustomLanguageCode(sourcepackagename, language_code):
        """Look up `ICustomLanguageCode`.

        A `SourcePackageName` in a Distribution may override some
        language codes for translation import purposes.
        """

    def userCanEdit(user):
        """Can the user edit this distribution?"""


class IDistribution(IDistributionEditRestricted, IDistributionPublic):
    """An operating system distribution."""
    export_as_webservice_entry()

# We are forced to define this now to avoid circular import problems.
IMessage['distribution'].schema = IDistribution

# Patch the official_bug_tags field to make sure that it's
# writable from the API, and not readonly like its definition
# in IHasBugs.
writable_obt_field = copy_field(IDistribution['official_bug_tags'])
writable_obt_field.readonly = False
IDistribution._v_attrs['official_bug_tags'] = writable_obt_field


class IDistributionSet(Interface):
    """Interface for DistrosSet"""
    export_as_webservice_collection(IDistribution)

    title = Attribute('Title')

    def __iter__():
        """Iterate over all distributions.

        Ubuntu and its flavours will always be at the top of the list, with
        the other ones sorted alphabetically after them.
        """

    def __getitem__(name):
        """Retrieve a distribution by name"""

    @collection_default_content()
    def getDistros(self):
        """Return all distributions.

        Ubuntu and its flavours will always be at the top of the list, with
        the other ones sorted alphabetically after them.
        """

    def count():
        """Return the number of distributions in the system."""

    def get(distributionid):
        """Return the IDistribution with the given distributionid."""

    def getByName(distroname):
        """Return the IDistribution with the given name or None."""

    def new(name, displayname, title, description, summary, domainname,
            members, owner, mugshot=None, logo=None, icon=None):
        """Creaste a new distribution."""


class NoSuchDistribution(NameLookupFailed):
    """Raised when we try to find a distribution that doesn't exist."""

    _message_prefix = "No such distribution"


# Monkey patching to fix circular imports.
from canonical.launchpad.components.apihelpers import (
    patch_entry_return_type, patch_collection_return_type,
    patch_reference_property)

from lp.registry.interfaces.distroseries import IDistroSeries
IDistribution['serieses'].value_type.schema = IDistroSeries
patch_reference_property(
    IDistribution, 'currentseries', IDistroSeries)
patch_entry_return_type(
    IDistribution, 'getSeries', IDistroSeries)
patch_collection_return_type(
    IDistribution, 'getDevelopmentSerieses', IDistroSeries)

from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage)
patch_entry_return_type(
    IDistribution, 'getSourcePackage', IDistributionSourcePackage)
patch_collection_return_type(
    IDistribution, 'searchSourcePackages', IDistributionSourcePackage)

from lp.soyuz.interfaces.archive import IArchive
patch_reference_property(
    IDistribution, 'main_archive', IArchive)
IDistribution['all_distro_archives'].value_type.schema = IArchive
