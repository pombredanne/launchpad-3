# Zope imports
from zope.interface import implements
from zope.component import getUtility

# interfaces and database 
from canonical.launchpad.interfaces import IBinaryPackageUtility
from canonical.launchpad.interfaces import IBinaryPackageSet

#
#
#

class BinaryPackageSet(object):
    """A Set of BinaryPackages"""
    implements(IBinaryPackageSet)
    def __init__(self, distrorelease, arch):
        self.distrorelease = distrorelease
        self.arch = arch
        self.title = 'Packages in ' + distrorelease.name + ', ' +arch

    def findPackagesByName(self, pattern):
        """Search BinaryPackages matching pattern"""
        binset = getUtility(IBinaryPackageUtility)
        return binset.findByNameInDistroRelease(self.distrorelease.id, pattern)

    def findPackagesByArchtagName(self, pattern, fti=False):
        """Search BinaryPackages matching pattern and archtag"""
        binset = getUtility(IBinaryPackageUtility)
        return binset.findByNameInDistroRelease(self.distrorelease.id,
                                                pattern, self.arch,
                                                fti)
        
    def __getitem__(self, name):
        binset = getUtility(IBinaryPackageUtility)
        try:
            return binset.getByNameInDistroRelease(self.distrorelease.id,
                                                   name=name,
                                                   archtag=self.arch)[0]
        except IndexError:
            raise KeyError
    
    def __iter__(self):
        binset = getUtility(IBinaryPackageUtility)
        return iter(binset.getByNameInDistroRelease(self.distrorelease.id,
                                                    archtag=self.arch))

