# Imports from zope
from zope.schema import Int, Text, TextLine
from zope.schema import Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

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
    bugtasks = Attribute("bugtasks")

    product = Attribute("Product, or None")
    proposed = Attribute("A source package release with upload status of "
                         "PROPOSED, else None")
    def bugsCounter():
        """A bug counter widget for sourcepackage"""

    def getBugSourcePackages(distrorelease):
        """Get SourcePackages in a DistroRelease with BugTasks"""

    def lastversions(distrorelease):
        """
        Get the lastest version of a
        sourcepackagerelease in a distrorelease
        """

    def current(distrorelease):
        """Current SourcePackageRelease of a SourcePackage"""


class ISourcePackageSet(Interface):
    """A set for ISourcePackage objects."""

    title = Attribute('Title')

    def __getitem__(key):
        """Get an ISourcePackage by name"""

    def __iter__():
        """Iterate through SourcePackages."""

    def withBugs():
        """Return a sequence of SourcePackage, that have bugs assigned to them
        (i.e. tasks.) In future, we might pass qualifiers to further limit the
        list that is returned, such as a name filter, or a bug task status
        filter."""

    def getSourcePackages(distroreleaseID):
        """Returns a set of SourcePackage in a DistroRelease"""

    def getByPersonID(personID):
        """Get a set of SourcePackages maintained by a Person"""
