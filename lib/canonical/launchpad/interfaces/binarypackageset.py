# Imports from zope
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

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

