# Imports from zope
from zope.schema import Bool, Int, Text, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


#
# Interface provided by a BinaryPackage
#
class IBinaryPackage(Interface):
    id = Int(title=_('ID'), required=True)
    #sourcepackagerelease = Int(required=True)
    binarypackagename = Int(required=True)
    version = TextLine(required=True)
    shortdesc = Text(required=True)
    description = Text(required=True)
    build = Int(required=True)
    binpackageformat = Int(required=True)
    component = Int(required=True)
    section = Int(required=True)
    priority = Int(required=False)
    shlibdeps = Text(required=False)
    depends = Text(required=False)
    recommends = Text(required=False)
    suggests = Text(required=False)
    conflicts = Text(required=False)
    replaces = Text(required=False)
    provides = Text(required=False)
    essential = Bool(required=False)
    installedsize = Int(required=False)
    copyright = Text(required=False)
    licence = Text(required=False)
    architecturespecific = Bool(required=True)

    files = Attribute("This BinaryPackage file")

    title = TextLine(required=True, readonly=True)
    name = Attribute("Binary Package Name")
    pkgpriority = Attribute("Package Priority")
    status = Attribute("The BinaryPackageStatus Title")
    files_url = Attribute("Return an URL to Download this Package")

    def current(distroRelease):
        """Get the current BinaryPackage in a distrorelease"""

    def lastversions():
        """Return the SUPERSEDED BinaryPackages in a DistroRelease
           that comes from the same SourcePackage"""

    def __getitem__(version):
        """Return the packagename that matches the given version"""


class IBinaryPackageSet(Interface):
    """A set of binary packages"""    
    
    distrorelease = Attribute("DistroRelease")

    arch = Attribute("Arch")

    title = Attribute('Title')

    def findPackagesByName(pattern):
        """Search BinaryPackages matching pattern"""

    def findPackagesByArchtagName(archtag, pattern, fti=False):
        """Search BinaryPackages matching pattern and archtag"""

    def __getitem__(name):
        """Getter"""    

    def __iter__():
        """Iterator"""    
