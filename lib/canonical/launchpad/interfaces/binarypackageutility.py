# Imports from zope
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class IBinaryPackageUtility(Interface):
    """A binary packages utility"""

    def getByNameInDistroRelease(distroreleaseID, name):
        """Get an BinaryPackage in a DistroRelease by its name"""

    def findByNameInDistroRelease(distroreleaseID, pattern,
                                  archtag=None, fti=False):
        """Returns a set of binarypackages that matchs pattern
        inside a distrorelease"""

    def getDistroReleasePackages(distroreleaseID):
        """Get a set of BinaryPackages in a distrorelease"""
    
    def getByNameVersion(distroreleaseID, name, version):
        """Get a set of BinaryPackages in a DistroRelease by its name and version"""

    def getByArchtag(distroreleaseID, name, version, archtag):
        """Get a BinaryPackage in a DistroRelease by its name, version and archtag"""

