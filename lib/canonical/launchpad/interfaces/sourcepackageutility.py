# Imports from zope
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class ISourcePackageUtility(Interface):
    """A Utility for SourcePackages"""
    def findByNameInDistroRelease(distroreleaseID, pattern):
        """Returns a set o sourcepackage that matchs pattern
        inside a distrorelease"""

    def getByNameInDistroRelease(distroreleaseID, name):
        """Returns a SourcePackage by its name"""

    def getSourcePackageRelease(sourcepackageid, version):
        """Get an Specific SourcePackageRelease by sourcepackageID and Version"""


