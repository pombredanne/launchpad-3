# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Distribution release interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroRelease',
    'IDistroReleaseSet',
    ]

from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

from canonical.launchpad.fields import Title, Summary, Description
from canonical.launchpad.interfaces import IHasOwner

_ = MessageIDFactory('launchpad')


class IDistroRelease(IHasOwner):
    """A Release Object"""
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
    bugtasks = Attribute("The bug tasks filed specifically on this release.")
    componentes = Attribute("The release componentes.")
    sections = Attribute("The release section.")
    releasestatus = Attribute(
        "The release's status, such as FROZEN or DEVELOPMENT, as "
        "specified in the DistributionReleaseStatus enum.")
    datereleased = Attribute("The datereleased.")
    parentrelease = Attribute("Parent Release")
    owner =Attribute("Owner")
    state = Attribute("DistroRelease Status")
    parent = Attribute("DistroRelease Parent")
    lucilleconfig = Attribute("Lucille Configuration Field")
    sourcecount = Attribute("Source Packages Counter")
    binarycount = Attribute("Binary Packages Counter")
    potemplates = Attribute("The set of potemplates in the release")
    potemplatecount = Attribute("The number of potemplates for this release")
    architecturecount = Attribute("The number of architectures in this "
        "release.")
    architectures = Attribute("The Architecture-specific Releases")
    datelastlangpack = Attribute(
        "The date of the last base language pack export for this release.")

    # related joins
    packagings = Attribute("All of the Packaging entries for this "
        "distrorelease.")

    previous_releases = Attribute("Previous distroreleases from the same "
        "distribution.")

    def getBugSourcePackages():
        """Get SourcePackages in a DistroRelease with BugTask"""

    def traverse(name):
        """Traverse across a distrorelease in Launchpad. This looks for
        special URL items, like +sources or +packages, then goes on to
        traverse using __getitem__."""

    def __getitem__(arch):
        """Return a Set of Binary Packages in this distroarchrelease."""

    def getSourcePackageByName(name):
        """Return a source package in this distro release by name.

        The name given may be a string or an ISourcePackageName-providing
        object.
        """

    def findBinariesByName(name):
        """Return an iterator over binary packages with a name that matches
        this one."""

    def getPublishedReleases(sourcepackage_or_name):
        """Given a SourcePackageName, return a list of the currently
        published SourcePackageReleases as SourcePackagePublishing records.
        """

    def publishedBinaryPackages(component=None):
        """Given an optional component name, return a list of the binary
        packages that are currently published in this distrorelease in the
        given component, or in any component if no component name was given.
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
