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
    IHasOwner, IBugTarget, ISpecificationTarget)

from canonical.launchpad import _

class IDistroRelease(IHasOwner, IBugTarget, ISpecificationTarget):
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
    components = Choice(
        title=_("Components"),
        description=_("The release components."), required=True,
        vocabulary='Schema')
    sections = Choice(
        title=_("Section"),
        description=_("The release sections."), required=True,
        vocabulary='Schema')
    # XXX: dsilvers: 20051013: These should be renamed and the above removed
    # in the future when we have time. Uploader and Queue systems will need
    # fixing to cope.
    # Bug 3256
    real_components = Attribute("The release's components.")
    real_sections = Attribute("The release's sections.")
    releasestatus = Attribute(
        "The release's status, such as FROZEN or DEVELOPMENT, as "
        "specified in the DistributionReleaseStatus enum.")
    datereleased = Attribute("The datereleased.")
    parentrelease = Choice(
        title=_("Parent Release"),
        description=_("The Parente Distribution Release."), required=True,
        vocabulary='DistroRelease')
    owner = Attribute("Owner")
    state = Attribute("DistroRelease Status")
    parent = Attribute("DistroRelease Parent")
    lucilleconfig = Attribute("Lucille Configuration Field")
    changeslist = Attribute("The changes list address for the distrorelease.")
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
    messagecount = Attribute("The total number of translatable items in "
        "this distribution release.")
    distroreleaselanguages = Attribute("The set of dr-languages in this "
        "release.")
    datelastlangpack = Attribute(
        "The date of the last base language pack export for this release.")

    translatable_sourcepackages = Attribute("Source packages in this "
        "distrorelease that can be translated.")

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

    open_cve_bugtasks = Attribute(
        "Any bugtasks on this distrorelease that are for bugs with "
        "CVE references, and are still open.")

    resolved_cve_bugtasks = Attribute(
        "Any bugtasks on this distrorelease that are for bugs with "
        "CVE references, and are resolved.")

    def traverse(name):
        """Traverse across a distrorelease in Launchpad. This looks for
        special URL items, like +sources or +packages, then goes on to
        traverse using __getitem__."""

    def __getitem__(archtag):
        """Return the distroarchrelease for this distrorelease with the
        given architecturetag.
        """

    def updateStatistics(self):
        """Update all the Rosetta stats for this distro release."""

    def findSourcesByName(name):
        """Return an iterator over source packages with a name that matches
        this one."""

    def getSourcePackage(name):
        """Return a source package in this distro release by name.

        The name given may be a string or an ISourcePackageName-providing
        object.
        """

    def getBinaryPackage(name):
        """Return a DistroReleaseBinaryPackage for this name.

        The name given may be an IBinaryPackageName or a string.
        """

    def findBinariesByName(name):
        """Return an iterator over binary packages with a name that matches
        this one."""

    def getPublishedReleases(sourcepackage_or_name, pocket=None):
        """Given a SourcePackageName, return a list of the currently
        published SourcePackageReleases as SourcePackagePublishing records.

        If pocket is not specified, we look in all pockets.
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

    def createUploadedSourcePackageRelease(sourcepackagename, version,
            maintainer, dateuploaded, builddepends, builddependsindep,
            architecturehintlist, component, creator, urgency,
            changelog, dsc, dscsigningkey, section, manifest):
        """Create a sourcepackagerelease with this distrorelease set to
        be the uploadeddistrorelease.
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

    def removeOldCacheItems():
        """Delete any records that are no longer applicable."""

    def updateCompletePackageCache():
        """Update the package cache for all binary package names published
        in this distro release.
        """

    def updatePackageCache(name):
        """Update the package cache for the binary packages with the given
        name.
        """

    def searchPackages(text):
        """Search through the packge cache for this distrorelease and return
        DistroReleaseBinaryPackage objects that match the given text.
        """

    def createQueueEntry(pocket):
        """Create a queue item attached to this distrorelease and the given
        pocket.
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
            version, components, sections, parentrelease, owner):
        """Creates a new distrorelease"""
