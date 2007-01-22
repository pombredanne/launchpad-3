# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces including and related to IDistroRelease."""

__metaclass__ = type

__all__ = [
    'IDistroRelease',
    'IDistroReleaseSet',
    ]

from zope.schema import Choice, Int, TextLine
from zope.interface import Interface, Attribute

from canonical.launchpad.fields import Title, Summary, Description
from canonical.launchpad.interfaces import (
    IHasOwner, IHasDrivers, IBugTarget, ISpecificationGoal)

from canonical.lp.dbschema import PackageUploadStatus
from canonical.launchpad.validators.email import valid_email

from canonical.launchpad import _

class IDistroRelease(IHasDrivers, IHasOwner, IBugTarget, ISpecificationGoal):
    """A specific release of an operating system distribution."""
    id = Attribute("The distrorelease's unique number.")
    name = TextLine(
        title=_("Name"), required=True,
        description=_("The name of this distribution release."))
    displayname = TextLine(
        title=_("Display name"), required=True,
        description=_("The release's displayname."))
    fullreleasename = TextLine(
        title=_("Release name"), required=False,
        description=_("The release's full name, e.g. Ubuntu Warty"))
    title = Title(
        title=_("Title"), required=True,
        description=_("""The title of this release. It should be distinctive
                      and designed to look good at the top of a page."""))
    summary = Summary(title=_("Summary"), required=True,
        description=_("A brief summary of the highlights of this release. "
                      "It should be no longer than a single paragraph, up "
                      "to 200 words."))
    description = Description(title=_("Description"), required=True,
        description=_("A detailed description of this release, with "
                      "information on the architectures covered, the "
                      "availability of security updates and any other "
                      "relevant information."))
    version = TextLine(title=_("Version"), required=True,
        description=_("The version string for this release."))
    distribution = Int(title=_("Distribution"), required=True,
        description=_("The distribution for which this is a release."))
    components = Attribute("The release's components.")
    sections = Attribute("The release's sections.")
    releasestatus = Choice(
        title=_("Release Status"), required=True,
        vocabulary='DistributionReleaseStatus')
    datereleased = Attribute("The datereleased.")
    parentrelease = Choice(
        title=_("Parent Release"),
        description=_("The Parent Distribution Release."), required=True,
        vocabulary='DistroRelease')
    owner = Attribute("Owner")
    driver = Choice(
        title=_("Driver"),
        description=_(
            "The person or team responsible for decisions about features "
            "and bugs that will be targeted to this release of the "
            "distribution."),
        required=False, vocabulary='ValidPersonOrTeam')
    changeslist = TextLine(
        title=_("Changeslist"), required=True,
        description=_("The changes list address for the distrorelease."),
        constraint=valid_email)
    state = Attribute("DistroRelease Status")
    parent = Attribute("DistroRelease Parent")
    lucilleconfig = Attribute("Lucille Configuration Field")
    sourcecount = Attribute("Source Packages Counter")
    binarycount = Attribute("Binary Packages Counter")
    potemplates = Attribute("The set of potemplates in the release")
    currentpotemplates = Attribute("The set of potemplates in the release "
        "with the iscurrent flag set")
    architecturecount = Attribute("The number of architectures in this "
        "release.")
    architectures = Attribute("The Architecture-specific Releases")
    nominatedarchindep = Attribute(
        "Distroarchrelease designed to build architeture independent "
        "packages whithin this distrorelease context.")
    milestones = Attribute(
        'The milestones associated with this distrorelease.')
    drivers = Attribute(
        'A list of the people or teams who are drivers for this release. '
        'This list is made up of any drivers or owners from this '
        'DistroRelease, and the Distribution to which it belong.')
    messagecount = Attribute("The total number of translatable items in "
        "this distribution release.")
    distroreleaselanguages = Attribute("The set of dr-languages in this "
        "release.")
    datelastlangpack = Attribute(
        "The date of the last base language pack export for this release.")

    # related joins
    packagings = Attribute("All of the Packaging entries for this "
        "distrorelease.")
    specifications = Attribute("The specifications targeted to this "
        "product series.")

    binary_package_caches = Attribute("All of the cached binary package "
        "records for this distrorelease.")

    # other properties
    previous_releases = Attribute("Previous distroreleases from the same "
        "distribution.")

    main_archive = Attribute('Main Archive')

    def isUnstable():
        """Return True if in unstable (or "development") phase, False otherwise.

        The distribution is unstable until it is released; after that
        point, all development on the Release pocket is stopped and
        development moves on to the other pockets.
        """

    def canUploadToPocket(pocket):
        """Decides whether or not allow uploads for a given pocket.

        Only allow uploads for RELEASE pocket in unreleased
        distroreleases and the opposite, only allow uploads for
        non-RELEASE pockets in released distroreleases.
        For instance, in edgy time :

                warty         -> DENY
                edgy          -> ALLOW
                warty-updates -> ALLOW
                edgy-security -> DENY

        Return True if the upload is allowed and False if denied.
        """

    def getLastUploads():
        """Return the last five source uploads for this DistroRelease.

        It returns a list containing up to five elements as
        IDistroReleaseSourcePackageRelease instances
        """

    def traverse(name):
        """Traverse across a distrorelease in Launchpad. This looks for
        special URL items, like +sources or +packages, then goes on to
        traverse using __getitem__."""

    def __getitem__(archtag):
        """Return the distroarchrelease for this distrorelease with the
        given architecturetag.
        """

    def updateStatistics():
        """Update all the Rosetta stats for this distro release."""

    def updatePackageCount():
        """Update the binary and source package counts for this distro
        release."""

    def findSourcesByName(name):
        """Return an iterator over source packages with a name that matches
        this one."""

    def getSourcePackage(name):
        """Return a source package in this distro release by name.

        The name given may be a string or an ISourcePackageName-providing
        object.
        """

    def getTranslatableSourcePackages():
        """Return a list of Source packages in this distribution release
        that can be translated.
        """

    def getUnlinkedTranslatableSourcePackages():
        """Return a list of source packages that can be translated in
        this distribution release but which lack Packaging links.
        """

    def getBinaryPackage(name):
        """Return a DistroReleaseBinaryPackage for this name.

        The name given may be an IBinaryPackageName or a string.
        """

    def getSourcePackageRelease(sourcepackagerelease):
        """Return a IDistroReleaseSourcePackageRelease

        sourcepackagerelease is an ISourcePackageRelease.
        """

    def findBinariesByName(name):
        """Return an iterator over binary packages with a name that matches
        this one."""

    def getPublishedReleases(sourcepackage_or_name, pocket=None,
                             include_pending=False, exclude_pocket=None):
        """Given a SourcePackageName, return a list of the currently
        published SourcePackageReleases as SourcePackagePublishing records.

        If pocket is not specified, we look in all pockets.

        if exclude_pocket is specified we exclude results matching that pocket.

        If 'include_pending' is True, we return also the pending publication
        records, those packages that will get published in the next publisher
        run (it's only useful when we need to know if a given package is
        known during a publisher run, mostly in pre-upload checks)
        """

    def getAllReleasesByStatus(status):
        """Return all sourcepackages in a given published_status for this
        DistroRelease.
        """

    def publishedBinaryPackages(component=None):
        """Given an optional component name, return a list of the binary
        packages that are currently published in this distrorelease in the
        given component, or in any component if no component name was given.
        """

    def getDistroReleaseLanguage(language):
        """Return the DistroReleaseLanguage for this distrorelease and the
        given language, or None if there's no DistroReleaseLanguage for this
        distribution and the given language.
        """

    def getDistroReleaseLanguageOrDummy(language):
        """Return the DistroReleaseLanguage for this distrorelease and the
        given language, or a DummyDistroReleaseLanguage.
        """

    def createUploadedSourcePackageRelease(
        sourcepackagename, version, maintainer, dateuploaded, builddepends,
        builddependsindep, architecturehintlist, component, creator, urgency,
        changelog, dsc, dscsigningkey, section, manifest,
        dsc_maintainer_rfc822, dsc_standards_version, dsc_format,
        dsc_binaries):
        """Create an uploads SourcePackageRelease

        Set this distrorelease set to be the uploadeddistrorelease.

        All arguments are mandatory, they are extracted/built when
        processing and uploaded source package:

         * dateuploaded: timestamp, usually UTC_NOW
         * sourcepackagename: ISourcePackageName
         * version: string, a debian valid version
         * maintainer: IPerson designed as package maintainer
         * creator: IPerson, package uploader
         * component: IComponent
         * section: ISection
         * urgency: dbschema.SourcePackageUrgency
         * manifest: IManifest
         * dscsigningkey: IGPGKey used to sign the DSC file
         * dsc: string, original content of the dsc file
         * changelog: string, changelog extracted from the changesfile
         * architecturehintlist: string, DSC architectures
         * builddepends: string, DSC build dependencies
         * builddependsindep: string, DSC architecture independent build
           dependencies.
         * dsc_maintainer_rfc822: string, DSC maintainer field
         * dsc_standards_version: string, DSC standards version field
         * dsc_format: string, DSC format version field
         * dsc_binaries:  string, DSC binaries field

        """

    def getComponentByName(name):
        """Get the named component.

        Raise NotFoundError if the component is not in the permitted component
        list for this distrorelease.
        """

    def getSectionByName(name):
        """Get the named section.

        Raise NotFoundError if the section is not in the permitted section
        list for this distrorelease.
        """

    def addComponent(component):
        """SQLObject provided method to fill a related join key component."""

    def addSection(section):
        """SQLObject provided method to fill a related join key section."""

    def getBinaryPackagePublishing(
        name=None, version=None, archtag=None, sourcename=None, orderBy=None,
        pocket=None, component=None, archive=None):
        """Get BinaryPackagePublishings in a DistroRelease.

        Can optionally restrict the results by name, version,
        architecturetag, pocket and/or component.

        If sourcename is passed, only packages that are built from
        source packages by that name will be returned.
        If archive is passed, restricted the results to the given archive,
        if it is suppressed the results will be restricted to the distribtion
        'main_archive'.
        """

    def getSourcePackagePublishing(status, pocket, component=None,
                                   archive=None):
        """Return a selectResult of ISourcePackagePublishing.

        According status and pocket.
        If archive is passed, restricted the results to the given archive,
        if it is suppressed the results will be restricted to the distribtion
        'main_archive'.
        """

    def removeOldCacheItems(log):
        """Delete any records that are no longer applicable.

        Consider all binarypackages marked as REMOVED.
        'log' is required, it should be a logger object able to print
        DEBUG level messages.
        """

    def updateCompletePackageCache(log, ztm):
        """Update the binary package cache

        Consider all binary package names published in this distro release.
        'log' is required, it should be a logger object able to print
        DEBUG level messages.
        """

    def updatePackageCache(name, log):
        """Update the package cache for a given IBinaryPackageName

        'log' is required, it should be a logger object able to print
        DEBUG level messages.
        'ztm' is the current trasaction manager used for partial commits
        (in full batches of 100 elements)
        """

    def searchPackages(text):
        """Search through the packge cache for this distrorelease and return
        DistroReleaseBinaryPackage objects that match the given text.
        """

    def createQueueEntry(pocket, changesfilename, changesfilecontent):
        """Create a queue item attached to this distrorelease and the given
        pocket.

        The default state is NEW, sorted sqlobject declaration, any
        modification should be performed via Queue state-machine.
        The changesfile argument should be the text of the .changes for this
        upload. The contents of this may be used later.
        """

    def newArch(architecturetag, processorfamily, official, owner):
        """Create a new port or DistroArchRelease for this DistroRelease."""

    def newMilestone(name, dateexpected=None):
        """Create a new milestone for this DistroRelease."""

    def initialiseFromParent():
        """Copy in all of the parent distrorelease's configuration. This
        includes all configuration for distrorelease and distroarchrelease
        publishing and all publishing records for sources and binaries.

        Preconditions:
          The distrorelease must have been set up with its distroarchreleases
          as needed. It should have its nominated arch-indep set up along
          with all other basic requirements for the structure of the
          distrorelease. This distrorelease and all its distroarchreleases
          must have empty publishing sets. Section and component selections
          must be empty.

        Outcome:
          The publishing structure will be copied from the parent. All
          PUBLISHED and PENDING packages in the parent will be created in
          this distrorelease and its distroarchreleases. The lucille config
          will be copied in, all component and section selections will be
          duplicated as will any permission-related structures.

        Note:
          This method will assert all of its preconditions where possible.
          After this is run, you still need to construct chroots for building,
          you need to add anything missing wrt. ports etc. This method is
          only meant to give you a basic copy of a parent release in order
          to assist you in preparing a new release of a distribution or
          in the initialisation of a derivative.
        """

    def copyMissingTranslationsFromParent(ztm=None):
        """Copy any translation done in parent that we lack.

        If there is another translation already added to this one, we ignore
        the one from parent.
        """

class IDistroReleaseSet(Interface):
    """The set of distro releases."""

    def get(distroreleaseid):
        """Retrieve the distro release with the given distroreleaseid."""

    def translatables():
        """Return a set of distroreleases that can be translated in
        rosetta."""

    def findByName(name):
        """Find a DistroRelease by name.

        Returns a list of matching distributions, which may be empty.
        """

    def queryByName(distribution, name):
        """Query a DistroRelease by name.

        :distribution: An IDistribution.
        :name: A string.

        Returns the matching DistroRelease, or None if not found.
        """

    def findByVersion(version):
        """Find a DistroRelease by version.

        Returns a list of matching distributions, which may be empty.
        """

    def search(distribution=None, released=None, orderBy=None):
        """Search the set of distro releases.

        released == True will filter results to only include
        IDistroReleases with releasestatus CURRENT or SUPPORTED.

        released == False will filter results to only include
        IDistroReleases with releasestatus EXPERIMENTAL, DEVELOPMENT,
        FROZEN.

        released == None will do no filtering on releasestatus.
        """

    def new(distribution, name, displayname, title, summary, description,
            version, parentrelease, owner):
        """Creates a new distrorelease"""
