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
    
    
# XXX: Daniel Debonzi 20050309
# I believe it is older tha I :)
# Will remove if nothing breaks

## class IBinaryPackageBuild(Interface):
##     """A binary package build, e.g apache-utils 2.0.48-4_i386"""
##     # See the BinaryPackageBuild table
    
##     version = Attribute("A version string")
##     maintainer = Attribute("Maintainer")
##     sourcePackageRelease = Attribute("An ISourcePackageRelease")
##     sourcepackage = Attribute("An ISourcePackage")
##     binaryPackage = Attribute("An ISourcePackageRelease")
##     processor = Attribute("An ISourcePackageRelease")
##     binpackageformat = Attribute("An ISourcePackageRelease")
##     datebuilt = Attribute("An ISourcePackageRelease")


# XXX: Daniel Debonzi 20050309
# Seems to be duplicated. We already have it in publishing.py
# Will remove if nothing breaks

## class IPackagePublishing(Interface):
##     binarypackage = Attribute("BinaryPackage")
##     distroarchrelease = Attribute("Distro Arch Relese")
##     packages = Attribute("Set of Packages inside a DistroRelease")
