# Zope schema imports
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

class IDistroArchRelease(Interface):
    """DistroArchRelease Table Interface"""
    distrorelease = Attribute("DistroRelease")
    processorfamily = Attribute("ProcessorFamily")
    architecturetag = Attribute("ArchitectureTag")
    owner = Attribute("Owner")
    chroot = Attribute("Chroot")
    
    #joins
    packages = Attribute('List of binary packages in this port.')

    # for page layouts etc
    title = Attribute('Title')

    # useful attributes
    binarycount = Attribute('Count of Binary Packages')

    def findPackagesByName(pattern):
        """Search BinaryPackages matching pattern"""

    def findPackagesByArchtagName(pattern, fti=False):
        """Search BinaryPackages matching pattern and archtag"""
        
    def __getitem__(name):
        """Getter"""

