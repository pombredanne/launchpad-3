# Imports from zope
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
#
#

class ISourcePackageInDistroSet(Interface):
    """A Set of SourcePackages in a given DistroRelease"""

    title = Attribute('Title')

    def findPackagesByName(pattern):
        """Find SourcePackages in a given DistroRelease matching pattern"""

    def __iter__():
        """Return the SourcePackageInDistroSet Iterator"""

    def __getitem__(name):
        """Return a SourcePackageRelease Published in a DistroRelease"""

