# Zope imports
from zope.interface import implements
from zope.component import getUtility

# launchpad imports
from canonical.database.sqlbase import quote
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageInDistroSet, \
     ISourcePackageUtility
from canonical.launchpad.database.vsourcepackagereleasepublishing import \
     VSourcePackageReleasePublishing

#
#
#

class SourcePackageInDistroSet(object):
    """A Set of SourcePackages in a given DistroRelease"""
    implements(ISourcePackageInDistroSet)
    def __init__(self, distrorelease):
        """Take the distrorelease when it makes part of the context"""
        self.distrorelease = distrorelease
        self.title = 'Source Packages in: ' + distrorelease.title

    def findPackagesByName(self, pattern, fti=False):
        srcutil = getUtility(ISourcePackageUtility)
        return srcutil.findByNameInDistroRelease(self.distrorelease.id,
                                                 pattern, fti)

    def __iter__(self):
        plublishing_status = dbschema.PackagePublishingStatus.PUBLISHED.value
        
        query = ('distrorelease = %d'
                 % (self.distrorelease.id))
        
        return iter(SourcePackageInDistro.select(query,
                                                 orderBy='VSourcePackageInDistro.name',
                                                 distinct=True))

    def __getitem__(self, name):
        plublishing_status = dbschema.PackagePublishingStatus.PUBLISHED.value

        query = ('distrorelease = %d AND publishingstatus=%d AND name=%s'
                 % (self.distrorelease.id, plublishing_status, quote(name)))

        try:
            return VSourcePackageReleasePublishing.select(query)[0]
        except IndexError:
            raise KeyError, name
            
            
