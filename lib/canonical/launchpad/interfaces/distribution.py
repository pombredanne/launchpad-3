# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces including and related to IDistribution."""

__metaclass__ = type

__all__ = [
    'IDistribution',
    'IDistributionSet',
    ]

from zope.schema import (
    Object, Choice, Int, Text, TextLine)
from zope.interface import (
    Interface, Attribute)

from canonical.launchpad import _
from canonical.launchpad.fields import (
    Title, Summary, Description)
from canonical.launchpad.interfaces.archive import IArchive
from canonical.launchpad.interfaces.karma import IKarmaContext
from canonical.launchpad.interfaces.mentoringoffer import IHasMentoringOffers
from canonical.launchpad.interfaces import (
    IBugTarget, IHasAppointedDriver, IHasDrivers, IHasOwner,
    IHasSecurityContact, ILaunchpadUsage, ISpecificationTarget)
from canonical.launchpad.interfaces.milestone import IHasMilestones
from canonical.launchpad.interfaces.announcement import IMakesAnnouncements
from canonical.launchpad.interfaces.sprint import IHasSprints
from canonical.launchpad.interfaces.translationgroup import (
    IHasTranslationGroup)
from canonical.launchpad.validators.name import name_validator
from canonical.launchpad.fields import (
    IconImageUpload, LogoImageUpload, MugshotImageUpload, PillarNameField)


class DistributionNameField(PillarNameField):
    """The pillar for a distribution."""
    @property
    def _content_iface(self):
        """Return the interface of this pillar object."""
        return IDistribution

class IDistribution(IBugTarget, IHasAppointedDriver, IHasDrivers,
    IHasMentoringOffers, IHasMilestones, IMakesAnnouncements, IHasOwner,
    IHasSecurityContact, IHasSprints, IHasTranslationGroup, IKarmaContext,
    ILaunchpadUsage, ISpecificationTarget):
    """An operating system distribution."""

    id = Attribute("The distro's unique number.")
    name = DistributionNameField(
        title=_("Name"),
        constraint=name_validator,
        description=_("The distro's name."), required=True)
    displayname = TextLine(
        title=_("Display Name"),
        description=_("The displayable name of the distribution."),
        required=True)
    title = Title(
        title=_("Title"),
        description=_("The distro's title."), required=True)
    summary = Summary(
        title=_("Summary"),
        description=_(
            "The distribution summary. A short paragraph "
            "describing the goals and highlights of the distro."),
        required=True)
    homepage_content = Text(
        title=_("Homepage Content"), required=False,
        description=_(
            "The content of this distribution's home page. Edit this and it "
            "will be displayed for all the world to see. It is NOT a wiki "
            "so you cannot undo changes."))
    icon = IconImageUpload(
        title=_("Icon"), required=False,
        default_image_resource='/@@/distribution',
        description=_(
            "A small image of exactly 14x14 pixels and at most 5kb in size, "
            "that can be used to identify this distribution. The icon will "
            "be displayed everywhere we list the distribution and link "
            "to it."))
    logo = LogoImageUpload(
        title=_("Logo"), required=False,
        default_image_resource='/@@/distribution-logo',
        description=_(
            "An image of exactly 64x64 pixels that will be displayed in "
            "the heading of all pages related to this distribution. It "
            "should be no bigger than 50kb in size."))
    mugshot = MugshotImageUpload(
        title=_("Brand"), required=False,
        default_image_resource='/@@/distribution-mugshot',
        description=_(
            "A large image of exactly 192x192 pixels, that will be displayed "
            "on this distribution's home page in Launchpad. It should be no "
            "bigger than 100kb in size. "))
    description = Description(
        title=_("Description"),
        description=_("The distro's description."),
        required=True)
    domainname = TextLine(
        title=_("Domain name"),
        description=_("The distro's domain name."), required=True)
    owner = Int(
        title=_("Owner"),
        description=_("The distro's owner."), required=True)
    date_created = Attribute("The date this distribution was registered.")
    bugcontact = Choice(
        title=_("Bug Contact"),
        description=_(
            "The person or team who will receive all bugmail for this "
            "distribution"),
        required=False, vocabulary='ValidPersonOrTeam')
    driver = Choice(
        title=_("Driver"),
        description=_(
            "The person or team responsible for decisions about features "
            "and bugs that will be targeted for any series in this "
            "distribution. Note that you can also specify a driver "
            "on each series who's permissions will be limited to that "
            "specific series."),
        required=False, vocabulary='ValidPersonOrTeam')
    drivers = Attribute(
        "Presents the distro driver as a list for consistency with "
        "IProduct.drivers where the list might include a project driver.")
    members = Choice(
        title=_("Members"),
        description=_("The distro's members team."), required=True,
        vocabulary='ValidPersonOrTeam')
    mirror_admin = Choice(
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
    serieses = Attribute("DistroSeries'es inside this Distribution")
    bounties = Attribute(_("The bounties that are related to this distro."))
    bugCounter = Attribute("The distro bug counter")
    source_package_caches = Attribute("The set of all source package "
        "info caches for this distribution.")
    is_read_only = Attribute(
        "True if this distro is just monitored by Launchpad, rather than "
        "allowing you to use Launchpad to actually modify the distro.")
    upload_sender = TextLine(
        title=_("Uploader sender"),
        description=_("The default upload processor sender name."),
        required=False)
    upload_admin = Choice(
        title=_("Upload Manager"),
        description=_("The distribution upload admin."),
        required=False, vocabulary='ValidPersonOrTeam')
    uploaders = Attribute(_(
        "DistroComponentUploader records associated with this distribution."))

    # properties
    currentseries = Attribute(
        "The current development series of this distribution. Note that "
        "all maintainerships refer to the current series. When people ask "
        "about the state of packages in the distribution, we should "
        "interpret that query in the context of the currentseries.")

    full_functionality = Attribute(
        "Whether or not we enable the full functionality of Launchpad for "
        "this distribution. Currently only Ubuntu and some derivatives "
        "get the full functionality of LP")

    translation_focus = Choice(
        title=_("Translation Focus"),
        description=_(
            "The DistroSeries that should get the translation effort focus."),
        required=False,
        vocabulary='FilteredDistroSeriesVocabulary')

    language_pack_admin = Choice(
        title=_("Language Pack Administrator"),
        description=_("The distribution language pack administrator."),
        required=False, vocabulary='ValidPersonOrTeam')

    main_archive = Object(
        title=_('Distribution Main Archive.'), readonly=True, schema=IArchive
        )

    all_distro_archives = Attribute(
        "A sequence of the distribution's non-PPA IArchives.")

    all_distro_archive_ids = Attribute(
        "A list containing the IDs of all the non-PPA archives.")

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

    def getDevelopmentSerieses():
        """Return the DistroSerieses which are marked as in development."""

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

    def getSourcePackage(name):
        """Return a DistributionSourcePackage with the given name for this
        distribution, or None.
        """

    def getSourcePackageRelease(sourcepackagerelease):
        """Returns an IDistributionSourcePackageRelease

        Receives a sourcepackagerelease.
        """

    def ensureRelatedBounty(bounty):
        """Ensure that the bounty is linked to this distribution. Return
        None.
        """

    def getDistroSeriesAndPocket(distroseriesname):
        """Return a (distroseries,pocket) tuple which is the given textual
        distroseriesname in this distribution."""

    def removeOldCacheItems(log):
        """Delete any cache records for removed packages."""

    def updateCompleteSourcePackageCache(log, ztm):
        """Update the source package cache.

        Consider every non-REMOVED sourcepackage.
        'log' is required an only prints debug level information.
        'ztm' is required for partial commits, every chunk of 50 updates
        are committed.
        """

    def updateSourcePackageCache(log, sourcepackagename):
        """Update cached source package details.

        Update cache details for a given ISourcePackageName, including
        generated binarypackage names, summary and description fti.
        'log' is required and only prints debug level information.
        """

    def searchSourcePackages(text):
        """Search for source packages that correspond to the given text.
        Returns a list of DistributionSourcePackage objects, in order of
        matching.
        """

    def getFileByName(filename, archive=None, source=True, binary=True):
        """Find and return a LibraryFileAlias for the filename supplied.

        The file returned will be one of those published in the distribution.

        If searching both source and binary, and the file is found in the
        source packages it'll return that over a file for a binary package.

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
        """Return only pending publication PPAs in this distribution."""

    def getArchiveByComponent(component_name):
        """Return the archive most appropriate for the component name.

        Where different components may imply a different archive (e.g.
        partner), this method will return the archive for that component.

        If the component_name supplied is unknown, None is returned.
        """


class IDistributionSet(Interface):
    """Interface for DistrosSet"""

    title = Attribute('Title')

    def __iter__():
        """Iterate over distributions."""

    def __getitem__(name):
        """Retrieve a distribution by name"""

    def count():
        """Return the number of distributions in the system."""

    def get(distributionid):
        """Return the IDistribution with the given distributionid."""

    def getByName(distroname):
        """Return the IDistribution with the given name or None."""

    def new(name, displayname, title, description, summary, domainname,
            members, owner, mugshot=None, logo=None, icon=None):
        """Creaste a new distribution."""
