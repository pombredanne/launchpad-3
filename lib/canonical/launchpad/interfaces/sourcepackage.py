# Imports from zope
from zope.schema import Int, Text, TextLine
from zope.schema import Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class ISourcePackage(Interface):
    """A SourcePackage. See the MagicSourcePackage specification. This
    interface preserves as much as possible of the old SourcePackage
    interface from the SourcePackage table, with the new table-less
    implementation."""

    id = Attribute("ID")

    maintainer = Attribute("Maintainer")

    name = Attribute("The text name of this source package, from "
                     "SourcePackageName.")

    displayname = Attribute("A displayname, constructed, for this package")

    title = Attribute("Title")

    format = Attribute("Source Package Format. This is the format of the "
                "current source package release for this name in this "
                "distribution or distrorelease. Calling this when there is "
                "no current sourcepackagerelease will raise an exception.")

    changelog = Attribute("The changelog of the currentrelease for this "
                "source package published in this distrorelease.")

    manifest = Attribute("The Manifest of the current SourcePackageRelease "
                    "published in this distribution / distrorelease.")

    distribution = Attribute("Distribution")

    distrorelease = Attribute("The DistroRelease for this SourcePackage")

    sourcepackagename = Attribute("SourcePackageName")

    bugtasks = Attribute("Bug Tasks that reference this Source Package name "
                    "in the context of this distribution.")

    product = Attribute("The best guess we have as to the Launchpad Product "
                    "associated with this SourcePackage.")

    productseries = Attribute("The best guess we have as to the Launchpad "
                    "ProductSeries for this Source Package. Try find "
                    "packaging information for this specific distrorelease "
                    "then try parent releases and previous ubuntu releases.")

    pendingrelease = Attribute("The latest source package release with "
                "a Publishing status of PENDING, if one exists for "
                "this distrorelease, else None.")

    currentrelease = Attribute("""The latest published SourcePackageRelease
        of a source package with this name in the distribution or
        distrorelease, or None if no source package with that name is
        published in this distrorelease.""")

    publishedreleases = Attribute("The complete set of source package "
        "releases currently published in this distrorelease. This does "
        "not include proposed releases, only those actually published. ")

    releases = Attribute("The full set of source package releases that "
        "have been published in this distrorelease under this source "
        "package name. The list should be sorted by version number.")
    
    releasehistory = Attribute("A list of all the source packages ever "
        "published in this Distribution (across all distroreleases) with "
        "this source package name. Note that the list spans "
        "distroreleases, and should be sorted by version number.")

    direct_packaging = Attribute("Return the Packaging record that is "
        "explicitly for this distrorelease and source package name, "
        "or None if such a record does not exist. You should probably "
        "use ISourcePackage.packaging, which will also look through the "
        "distribution ancestry to find a relevant packaging record.")

    packaging = Attribute("The best Packaging record we have for this "
        "source package. If we have one for this specific distrorelease "
        "and sourcepackagename, it will be returned, otherwise we look "
        "for a match in parent and ubuntu distro releases.")

    def setPackaging(productseries, owner):
        """Update the existing packaging record, or create a new packaging
        record, that links the source package to the given productseries,
        and record that it was done by the owner.
        """

    def potemplates():
        """Returns the set of POTemplates that exist for this
        distrorelease/sourcepackagename combination."""

    potemplatecount = Attribute("The number of POTemplates for this "
                        "SourcePackage.")

    def bugsCounter():
        """A bug counter widget for sourcepackage. This finds the number of
        bugs for each bug severity, as well as the total number of bugs
        associated with this sourcepackagename in this distribution."""

    def getVersion(version):
        """Returns the SourcePackageRelease that had the name of this
        SourcePackage and the given version, and was published in this
        distribution. NB:
        
          1. Currently, we have no PublishingMorgue, so this will only find
             SourcePackageReleases that are *still* published (even if they
             have been superceded, as long as they have not yet been
             deleted).
        
          2. It will look across the entire distribution, not just in the
          current distrorelease. In Ubuntu and RedHat, and similar
          distributions, a sourcepackagerelease name+version is UNIQUE
          across all distroreleases. This may turn out not to be true in
          other types of distribution, such as Gentoo.
        """

    shouldimport = Attribute("""Whether we should import this or not.
        By "import" we mean sourcerer analysis resulting in a manifest and a
        set of Bazaar branches which describe the source package release.
        The attribute is True or False.""")


class ISourcePackageSet(Interface):
    """A set for ISourcePackage objects."""

    title = Attribute('Title')

    distribution = Attribute('Distribution')

    distrorelease = Attribute('DistroRelease')

    def __getitem__(key):
        """Get an ISourcePackage by name"""

    def __iter__():
        """Iterate through SourcePackages."""

    def query(text=None):
        """Return an interator over source packages that match the required
        text in this distrorelease / distribution."""

    def withBugs():
        """Return a sequence of SourcePackage, that have bugs assigned to them
        (i.e. tasks.) In future, we might pass qualifiers to further limit the
        list that is returned, such as a name filter, or a bug task status
        filter."""

    def getSourcePackages(distroreleaseID):
        """Returns a set of SourcePackage in a DistroRelease"""

    def findByNameInDistroRelease(distroreleaseID, pattern):
        """Returns a set of sourcepackages that matchs pattern
        inside a distrorelease.
        """

    def getByNameInDistroRelease(distroreleaseID, name):
        """Returns a SourcePackage by its name"""

    def getSourcePackageRelease(sourcepackageid, version):
        """Get a specific SourcePackageRelease by
        sourcepackageID and Version.
        """

    def getPackageNames(pkgname):
        """Find the actual source and binary package names to use when all
        we have it a name, that could be either a source or a binary package
        name. Returns a tuple of (sourcepackagename, binarypackagename)
        based on the current publishing status of these binary / source
        packages.
        """

