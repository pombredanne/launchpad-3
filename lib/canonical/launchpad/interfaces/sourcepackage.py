# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, TextLine
from zope.schema import Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class IPackages(Interface):
    """Root object for web app."""
    binary = Attribute("Binary packages")
    source = Attribute("Source packages")

    def __getitem__(name):
        """Retrieve a package set by name."""

class IPackageSet(Interface):
    """A set of packages"""
    def __getitem__(name):
        """Retrieve a package by name."""
    def __iter__():
        """Iterate over names"""

#
# Interface we expect a SourcePackage to provide.
#
class ISourcePackage(Interface):
    """A SourcePackage"""
    id = Int(title=_("ID"), required=True)
    name = TextLine(title=_("Name"), required=True)
    maintainer = Int(title=_("Maintainer"), required=True)
    title = TextLine(title=_("Title"), required=True)
    shortdesc = Text(title=_("Description"), required=True)
    srcpackageformat = Int(title=_('Source package format'), required=True)
    description = Text(title=_("Description"), required=True)
    manifest = Int(title=_("Manifest"), required=False)
    distro = Int(title=_("Distribution"), required=False)
    sourcepackagename = Int(title=_("Source package name"), required=True)
    bugs = Attribute("bugs")

    product = Attribute("Product, or None")
    proposed = Attribute("A source package release with upload status of "
                         "PROPOSED, else None")
    def bugsCounter():
        """A bug counter widget for sourcepackage"""

    def getBugSourcePackages(distrorelease):
        """Get SourcePackages in a DistroRelease with BugAssignement"""

    def lastversions(distrorelease):
        """
        Get the lastest version of a
        sourcepackagerelease in a distrorelease
        """
        
class ISourcePackageinDistro(Interface):
    """A SourcePackage in Distro PG View"""
    id = Int(title=_("ID"), required=True)
    name = TextLine(title=_("Name"), required=True)
    distrorelease = Int(title=_("DistroRelease"), required=False)
    maintainer = Int(title=_("Maintainer"), required=True)
    title = TextLine(title=_("Title"), required=True)
    shortdesc = Text(title=_("Description"), required=True)
    description = Text(title=_("Description"), required=True)
    manifest = Int(title=_("Manifest"), required=False)
    distro = Int(title=_("Distribution"), required=False)
    sourcepackagename = Int(title=_("SourcePackage Name"), required=True)
    bugs = Attribute("bugs")
    product = Attribute("Product, or None")
    proposed = Attribute("A source package release with upload status of "
                         "PROPOSED, else None")

    def bugsCounter():
        """A bug counter widget for sourcepackage"""
    releases = Attribute("Set of releases tha this package is inside")
    current = Attribute("Set of current versions")
    lastversions = Attribute("set of lastversions")


#
# Interface provied by a SourcePackageName. This is a tiny
# table that allows multiple SourcePackage entities to share
# a single name.
#
class ISourcePackageName(Interface):
    """Name of a SourcePackage"""
    id = Int(title=_("ID"), required=True)
    name = TextLine(title=_("Name"), required=True)


class ISourcePackageSet(Interface):
    """A set for ISourcePackage objects."""

    def __getitem__(key):
        """Get an ISourcePackage by name"""

    def __iter__():
        """Iterate through SourcePackages."""

    def withBugs():
        """Return a sequence of SourcePackage, that have bugs assigned to
        them. In future, we might pass qualifiers to further limit the list
        that is returned, such as a name filter, or a bug assignment status
        filter."""

    def getSourcePackages(distroreleaseID):
        """Returns a set of SourcePackage in a DistroRelease"""

    def getByPersonID(personID):
        """Get a set of SourcePackages maintained by a Person"""


class ISourcePackageInDistroSet(Interface):
    """A Set of SourcePackages in a given DistroRelease"""

    def findPackagesByName(pattern):
        """Find SourcePackages in a given DistroRelease matching pattern"""

    def __iter__():
        """Return the SourcePackageInDistroSet Iterator"""

    def __getitem__(name):
        """Return a SourcePackageRelease Published in a DistroRelease"""

class ISourcePackageUtility(Interface):
    """A Utility for SourcePackages"""
    def findByNameInDistroRelease(distroreleaseID, pattern):
        """Returns a set o sourcepackage that matchs pattern
        inside a distrorelease"""

    def getByNameInDistroRelease(distroreleaseID, name):
        """Returns a SourcePackage by its name"""

    def getSourcePackageRelease(sourcepackageid, version):
        """Get an Specific SourcePackageRelease by sourcepackageID and Version"""


class ISourcePackageRelease(Interface):
    """A source package release, e.g. apache-utils 2.0.48-3"""

    sourcepackage = Attribute("The source package this is a release for")
    creator = Attribute("Person that created this release")
    version = Attribute("A version string")
    dateuploaded = Attribute("Date of Upload")
    urgency = Attribute("Source Package Urgency")
    dscsigningkey = Attribute("DSC Signing Key")
    component = Attribute("Source Package Component")
    changelog = Attribute("Source Package Change Log")
    builddepends = Attribute(
        "A comma-separated list of packages on which this package"
        " depends to build")
    builddependsindep = Attribute(
        "Same as builddepends, but the list is of arch-independent packages")
    architecturehintlist = Attribute("XXX: Kinnison?")
    dsc = Attribute("The DSC file for this SourcePackageRelease")
    section = Attribute("Section this Source package Release belongs to")
    pkgurgency = Attribute("Source Package Urgency Translated using dbschema")
    binaries = Attribute(
        "Binary Packages generated by this SourcePackageRelease") 
    builds = Attribute("Builds for this sourcepackagerelease")

    def branches():
        """Return the list of branches in a source package release"""

    # XXX: What do the following methods and attributes do?
    #      These were missing from the interfaces, but being used
    #      in application code.
    #      -- Steve Alexander, Fri Dec 10 14:28:41 UTC 2004
    architecturesReleased = Attribute("XXX")

class ISourcePackageReleasePublishing(ISourcePackageRelease):
    """
    Interface for the SQL VSourcePackageReleasePublishing View, which
    aggregates data from sourcepackagerelease, sourcepackagepublishing,
    sourcepackagename, component and distrorelease.
    """
    id = Int(title=_("ID"), required=True)
    publishingstatus = Attribute("The status of this publishing record")
    datepublished = Attribute("The date on which this record was published")
    name = Attribute("The SourcePackage name")
    shortdesc = Attribute("The SourcePackage short description")
    description = Attribute("The SourcePackage description")
    componentname = Attribute("The Component name")
    distrorelease = Attribute("The distro in which this package was released")
    maintainer = Attribute("The maintainer of this package")

    def __getitem__(version):
        """Get a SourcePackageRelease"""

class IbuilddepsSet(Interface):
    name = Attribute("Package name for a builddepends/builddependsindep")
    signal = Attribute("Dependence Signal e.g = >= <= <")
    version = Attribute("Package version for a builddepends/builddependsindep")

class ICurrentVersion(Interface):
    release = Attribute("The binary or source release object")
    currentversion = Attribute("Current version of A binary or source package")
    currentbuilds = Attribute(
        "The current builds for binary or source package")

