# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces including and related to IDistroSeries."""

__metaclass__ = type

__all__ = [
    'DistroSeriesStatus',
    'IDistroSeries',
    'IDistroSeriesSet',
    ]

from zope.schema import Bool, Choice, Int, Object, TextLine
from zope.interface import Interface, Attribute

from canonical.launchpad.fields import Title, Summary, Description
from canonical.launchpad.interfaces.bugtarget import IBugTarget
from canonical.launchpad.interfaces.languagepack import ILanguagePack
from canonical.launchpad.interfaces.launchpad import (
    IHasAppointedDriver, IHasOwner, IHasDrivers)
from canonical.launchpad.interfaces.specificationtarget import (
    ISpecificationGoal)

from canonical.launchpad.validators.email import valid_email

from canonical.launchpad import _

from canonical.lazr import DBEnumeratedType, DBItem

class DistroSeriesStatus(DBEnumeratedType):
    """Distribution Release Status

    A DistroSeries (warty, hoary, or grumpy for example) changes state
    throughout its development. This schema describes the level of
    development of the distroseries. The typical sequence for a
    distroseries is to progress from experimental to development to
    frozen to current to supported to obsolete, in a linear fashion.
    """

    EXPERIMENTAL = DBItem(1, """
        Experimental

        This distroseries contains code that is far from active
        release planning or management. Typically, distroseriess
        that are beyond the current "development" release will be
        marked as "experimental". We create those so that people
        have a place to upload code which is expected to be part
        of that distant future release, but which we do not want
        to interfere with the current development release.
        """)

    DEVELOPMENT = DBItem(2, """
        Active Development

        The distroseries that is under active current development
        will be tagged as "development". Typically there is only
        one active development release at a time. When that freezes
        and releases, the next release along switches from "experimental"
        to "development".
        """)

    FROZEN = DBItem(3, """
        Pre-release Freeze

        When a distroseries is near to release the administrators
        will freeze it, which typically means that new package uploads
        require significant review before being accepted into the
        release.
        """)

    CURRENT = DBItem(4, """
        Current Stable Release

        This is the latest stable release. Normally there will only
        be one of these for a given distribution.
        """)

    SUPPORTED = DBItem(5, """
        Supported

        This distroseries is still supported, but it is no longer
        the current stable release. In Ubuntu we normally support
        a distroseries for 2 years from release.
        """)

    OBSOLETE = DBItem(6, """
        Obsolete

        This distroseries is no longer supported, it is considered
        obsolete and should not be used on production systems.
        """)


class IDistroSeries(IHasAppointedDriver, IHasDrivers, IHasOwner, IBugTarget,
                     ISpecificationGoal):
    """A series of an operating system distribution."""
    id = Attribute("The distroseries's unique number.")
    name = TextLine(
        title=_("Name"), required=True,
        description=_("The name of this series."))
    displayname = TextLine(
        title=_("Display name"), required=True,
        description=_("The series displayname."))
    fullseriesname = TextLine(
        title=_("Series full name"), required=False,
        description=_("The series full name, e.g. Ubuntu Warty"))
    title = Title(
        title=_("Title"), required=True,
        description=_("""The title of this series. It should be distinctive
                      and designed to look good at the top of a page."""))
    summary = Summary(title=_("Summary"), required=True,
        description=_("A brief summary of the highlights of this release. "
                      "It should be no longer than a single paragraph, up "
                      "to 200 words."))
    description = Description(title=_("Description"), required=True,
        description=_("A detailed description of this series, with "
                      "information on the architectures covered, the "
                      "availability of security updates and any other "
                      "relevant information."))
    version = TextLine(title=_("Version"), required=True,
        description=_("The version string for this series."))
    distribution = Int(title=_("Distribution"), required=True,
        description=_("The distribution for which this is a series."))
    parent = Attribute('The structural parent of this series - the distro')
    components = Attribute("The series components.")
    upload_components = Attribute("The series components that can be "
                                  "uploaded to.")
    sections = Attribute("The series sections.")
    status = Choice(
        title=_("Status"), required=True,
        vocabulary=DistroSeriesStatus)
    datereleased = Attribute("The datereleased.")
    parent_series = Choice(
        title=_("Parent series"),
        description=_("The series from which this one was branched."),
        required=True,
        vocabulary='DistroSeries')
    owner = Attribute("Owner")
    date_created = Attribute("The date this series was registered.")
    driver = Choice(
        title=_("Driver"),
        description=_(
            "The person or team responsible for decisions about features "
            "and bugs that will be targeted to this series of the "
            "distribution."),
        required=False, vocabulary='ValidPersonOrTeam')
    changeslist = TextLine(
        title=_("Changeslist"), required=True,
        description=_("The changes list address for the distroseries."),
        constraint=valid_email)
    lucilleconfig = Attribute("Lucille Configuration Field")
    sourcecount = Attribute("Source Packages Counter")
    defer_translation_imports = Bool(
        title=_("Defer translation imports"),
        description=_("Suspends any translation imports for this series"),
        default=True,
        required=True
        )
    binarycount = Attribute("Binary Packages Counter")

    architecturecount = Attribute("The number of architectures in this "
        "series.")
    architectures = Attribute("All architectures in this series.")
    ppa_architectures = Attribute(
        "All architectures in this series where PPA is supported.")
    nominatedarchindep = Attribute(
        "DistroArchSeries designed to build architecture-independent "
        "packages whithin this distroseries context.")
    milestones = Attribute(_(
        "The visible milestones associated with this series, "
        "ordered by date expected."))
    all_milestones = Attribute(_(
        "All milestones associated with this distroseries, ordered "
        "by date expected."))
    drivers = Attribute(
        'A list of the people or teams who are drivers for this series. '
        'This list is made up of any drivers or owners from this '
        'DistroSeries, and the Distribution to which it belong.')
    bugcontact = Attribute(
        'Currently just a reference to the Distribution bug contact.')
    security_contact = Attribute(
        'Currently just a reference to the Distribution security contact.')
    messagecount = Attribute("The total number of translatable items in "
        "this series.")
    distroserieslanguages = Attribute("The set of dr-languages in this "
        "series.")

    hide_all_translations = Bool(
        title=u'Hide translations for this release', required=True,
        description=(
            u"You may hide all translation for this distribution series so"
             " that only Launchpad administrators will be able to see them."
             " For example, you should hide these translations while they are"
             " being imported from a previous series so that translators"
             " will not be confused by imports that are in progress."),
        default=True)

    language_pack_base = Choice(
        title=_('Language pack base'), required=False,
        description=_('''
            Language pack export with the export of all translations available
            for this `IDistroSeries` when it was generated. Next delta exports
            will be generated based on this one.
            '''), vocabulary='FilteredFullLanguagePack')

    language_pack_delta = Choice(
        title=_('Language pack delta'), required=False,
        description=_('''
            Language pack export with the export of all translation updates
            available for this `IDistroSeries` since language_pack_base was
            generated.
            '''), vocabulary='FilteredDeltaLanguagePack')

    language_pack_proposed = Choice(
        title=_('Proposed language pack update'), required=False,
        description=_('''
            Base or delta language pack export that is being tested and
            proposed to be used as the new language_pack_base or
            language_pack_delta for this `IDistroSeries`.
            '''), vocabulary='FilteredLanguagePack')

    language_pack_full_export_requested = Bool(
        title=_('Request a full language pack export'), required=True,
        description=_('''
            Whether next language pack generation will be a full export. This
            is useful when delta packages are too big and want to merge all
            those changes in the base package.
            '''))

    last_full_language_pack_exported = Object(
        title=_('Latest exported language pack with all translation files.'),
        required=False, readonly=True, schema=ILanguagePack)

    last_delta_language_pack_exported = Object(
        title=_(
            'Lastest exported language pack with updated translation files.'),
        required=False, readonly=True, schema=ILanguagePack)

    # related joins
    packagings = Attribute("All of the Packaging entries for this "
        "distroseries.")
    specifications = Attribute("The specifications targeted to this "
        "series.")

    binary_package_caches = Attribute("All of the cached binary package "
        "records for this distroseries.")

    language_packs = Attribute(
        "All language packs associated with this distribution series.")

    # other properties
    previous_serieses = Attribute("Previous series from the same "
        "distribution.")

    main_archive = Attribute('Main Archive')

    supported = Attribute(
        "Whether or not this series is currently supported.")

    active = Attribute(
        "Whether or not this series is stable and supported, or under "
        "current development. This excludes series which are experimental "
        "or obsolete.")

    def isUnstable():
        """Whether or not a distroseries is unstable.

        The distribution is "unstable" until it is released; after that
        point, all development on the Release pocket is stopped and
        development moves on to the other pockets.
        """

    def canUploadToPocket(pocket):
        """Decides whether or not allow uploads for a given pocket.

        Only allow uploads for RELEASE pocket in unreleased
        distroseries and the opposite, only allow uploads for
        non-RELEASE pockets in released distroseries.
        For instance, in edgy time :

                warty         -> DENY
                edgy          -> ALLOW
                warty-updates -> ALLOW
                edgy-security -> DENY

        Note that FROZEN is not considered either 'stable' or 'unstable' state.
        Uploads to a FROZEN distroseries will end up in UNAPPROVED queue.

        Return True if the upload is allowed and False if denied.
        """

    def getLatestUploads():
        """Return the latest five source uploads for this DistroSeries.

        It returns a list containing up to five elements as
        IDistroSeriesSourcePackageRelease instances
        """

    def __getitem__(archtag):
        """Return the distroarchseries for this distroseries with the
        given architecturetag.
        """

    def updateStatistics(ztm):
        """Update all the Rosetta stats for this distro series."""

    def updatePackageCount():
        """Update the binary and source package counts for this distro
        series."""

    def getSourcePackage(name):
        """Return a source package in this distro series by name.

        The name given may be a string or an ISourcePackageName-providing
        object.
        """

    def getTranslatableSourcePackages():
        """Return a list of Source packages in this distribution series
        that can be translated.
        """

    def getUnlinkedTranslatableSourcePackages():
        """Return a list of source packages that can be translated in
        this distribution series but which lack Packaging links.
        """

    def getBinaryPackage(name):
        """Return a DistroSeriesBinaryPackage for this name.

        The name given may be an IBinaryPackageName or a string.
        """

    def getSourcePackageRelease(sourcepackagerelease):
        """Return a IDistroSeriesSourcePackageRelease

        sourcepackagerelease is an ISourcePackageRelease.
        """

    def getPublishedReleases(sourcepackage_or_name, pocket=None, version=None,
                             include_pending=False, exclude_pocket=None,
                             archive=None):
        """Return the SourcePackagePublishingHistory(s)

        Given a ISourcePackageName or name.

        If pocket is not specified, we look in all pockets.

        If version is not specified, return packages with any version.

        if exclude_pocket is specified we exclude results matching that pocket.

        If 'include_pending' is True, we return also the pending publication
        records, those packages that will get published in the next publisher
        run (it's only useful when we need to know if a given package is
        known during a publisher run, mostly in pre-upload checks)

        If 'archive' is not specified consider publication in the main_archive,
        otherwise respect the given value.
        """

    def getAllPublishedSources():
        """Return all currently published sources for the distroseries.

        Return publications in the main archives only.
        """

    def getAllPublishedBinaries():
        """Return all currently published binaries for the distroseries.

        Return publications in the main archives only.
        """

    def getSourcesPublishedForAllArchives():
        """Return all sourcepackages published across all the archives.

        It's only used in the buildmaster/master.py context for calculating
        the publication that are still missing build records.

        It will consider all publishing records in PENDING or PUBLISHED status
        as part of the 'build-unpublished-source' specification.

        For 'main_archive' candidates it will automatically exclude RELEASE
        pocket records of released distroseries (ensuring that we won't waste
        time with records that can't be accepted).

        Return a SelectResult of SourcePackagePublishingHistory.
        """

    def publishedBinaryPackages(component=None):
        """Given an optional component name, return a list of the binary
        packages that are currently published in this distroseries in the
        given component, or in any component if no component name was given.
        """

    def getDistroSeriesLanguage(language):
        """Return the DistroSeriesLanguage for this distroseries and the
        given language, or None if there's no DistroSeriesLanguage for this
        distribution and the given language.
        """

    def getDistroSeriesLanguageOrDummy(language):
        """Return the DistroSeriesLanguage for this distroseries and the
        given language, or a DummyDistroSeriesLanguage.
        """

    def createUploadedSourcePackageRelease(
        sourcepackagename, version, maintainer, builddepends,
        builddependsindep, architecturehintlist, component, creator, urgency,
        changelog, dsc, dscsigningkey, section, dsc_maintainer_rfc822,
        dsc_standards_version, dsc_format, dsc_binaries, archive, copyright,
        dateuploaded=None):
        """Create an uploads SourcePackageRelease

        Set this distroseries set to be the uploadeddistroseries.

        All arguments are mandatory, they are extracted/built when
        processing and uploaded source package:

         * dateuploaded: timestamp, if not provided will be UTC_NOW
         * sourcepackagename: ISourcePackageName
         * version: string, a debian valid version
         * maintainer: IPerson designed as package maintainer
         * creator: IPerson, package uploader
         * component: IComponent
         * section: ISection
         * urgency: dbschema.SourcePackageUrgency
         * dscsigningkey: IGPGKey used to sign the DSC file
         * dsc: string, original content of the dsc file
         * copyright: string, the original debian/copyright content
         * changelog: string, changelog extracted from the changesfile
         * architecturehintlist: string, DSC architectures
         * builddepends: string, DSC build dependencies
         * builddependsindep: string, DSC architecture independent build
           dependencies.
         * dsc_maintainer_rfc822: string, DSC maintainer field
         * dsc_standards_version: string, DSC standards version field
         * dsc_format: string, DSC format version field
         * dsc_binaries:  string, DSC binaries field
         * archive: IArchive to where the upload was targeted
         * dateuploaded: optional datetime, if omitted assumed nowUTC
        """

    def getComponentByName(name):
        """Get the named component.

        Raise NotFoundError if the component is not in the permitted component
        list for this distroseries.
        """

    def getSectionByName(name):
        """Get the named section.

        Raise NotFoundError if the section is not in the permitted section
        list for this distroseries.
        """

    def addSection(section):
        """SQLObject provided method to fill a related join key section."""

    def getBinaryPackagePublishing(
        name=None, version=None, archtag=None, sourcename=None, orderBy=None,
        pocket=None, component=None, archive=None):
        """Get BinaryPackagePublishings in a DistroSeries.

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
        """Return a selectResult of ISourcePackagePublishingHistory.

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

        Consider all binary package names published in this distro series.
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
        """Search through the packge cache for this distroseries and return
        DistroSeriesBinaryPackage objects that match the given text.
        """

    def createQueueEntry(pocket, changesfilename, changesfilecontent,
                         archive, signingkey=None):
        """Create a queue item attached to this distroseries.

        Create a new records respecting the given pocket and archive.

        The default state is NEW, sorted sqlobject declaration, any
        modification should be performed via Queue state-machine.

        The changesfile argument should be the text of the .changes for this
        upload. The contents of this may be used later.

        'signingkey' is the IGPGKey used to sign the changesfile or None if
        the changesfile is unsigned.
        """

    def newArch(architecturetag, processorfamily, official, owner,
                ppa_supported):
        """Create a new port or DistroArchSeries for this DistroSeries."""

    def newMilestone(name, dateexpected=None, description=None):
        """Create a new milestone for this DistroSeries."""

    def initialiseFromParent():
        """Copy in all of the parent distroseries's configuration. This
        includes all configuration for distroseries and distroarchseries
        publishing and all publishing records for sources and binaries.

        Preconditions:
          The distroseries must have been set up with its distroarchseriess
          as needed. It should have its nominated arch-indep set up along
          with all other basic requirements for the structure of the
          distroseries. This distroseries and all its distroarchseriess
          must have empty publishing sets. Section and component selections
          must be empty.

        Outcome:
          The publishing structure will be copied from the parent. All
          PUBLISHED and PENDING packages in the parent will be created in
          this distroseries and its distroarchseriess. The lucille config
          will be copied in, all component and section selections will be
          duplicated as will any permission-related structures.

        Note:
          This method will assert all of its preconditions where possible.
          After this is run, you still need to construct chroots for building,
          you need to add anything missing wrt. ports etc. This method is
          only meant to give you a basic copy of a parent series in order
          to assist you in preparing a new series of a distribution or
          in the initialisation of a derivative.
        """

    def copyMissingTranslationsFromParent(ztm):
        """Copy any translation done in parent that we lack.

        If there is another translation already added to this one, we ignore
        the one from parent.

        The supplied transaction manager will be used for intermediate
        commits to break up large copying jobs into palatable smaller
        chunks.
        """

class IDistroSeriesSet(Interface):
    """The set of distro seriess."""

    def get(distroseriesid):
        """Retrieve the distro series with the given distroseriesid."""

    def translatables():
        """Return a set of distroseriess that can be translated in
        rosetta."""

    def findByName(name):
        """Find a DistroSeries by name.

        Returns a list of matching distributions, which may be empty.
        """

    def queryByName(distribution, name):
        """Query a DistroSeries by name.

        :distribution: An IDistribution.
        :name: A string.

        Returns the matching DistroSeries, or None if not found.
        """

    def findByVersion(version):
        """Find a DistroSeries by version.

        Returns a list of matching distributions, which may be empty.
        """

    def search(distribution=None, released=None, orderBy=None):
        """Search the set of distro seriess.

        released == True will filter results to only include
        IDistroSeries with status CURRENT or SUPPORTED.

        released == False will filter results to only include
        IDistroSeriess with status EXPERIMENTAL, DEVELOPMENT,
        FROZEN.

        released == None will do no filtering on status.
        """

    def new(distribution, name, displayname, title, summary, description,
            version, parent_series, owner):
        """Creates a new distroseries"""
