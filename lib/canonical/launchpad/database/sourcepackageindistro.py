# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import MultipleJoin
from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, ForeignKey, MultipleJoin

# launchpad imports
from canonical.database.sqlbase import quote
from canonical.lp import dbschema

# launchpad interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageInDistro
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.interfaces import ISourcePackageInDistroSet, \
     ISourcePackageSet
from canonical.launchpad.database.vsourcepackagereleasepublishing import \
     VSourcePackageReleasePublishing

#
#
#

class SourcePackageInDistro(SourcePackage):
    implements(ISourcePackageInDistro)
    """
    Represents source packages that have releases published in the
    specified distribution. This view's contents are uniqued, for the
    following reason: a certain package can have multiple releases in a
    certain distribution release.
    """
    _table = 'VSourcePackageInDistro'
   
    #
    # Columns
    #
    name = StringCol(dbName='name', notNull=True)

    distrorelease = ForeignKey(foreignKey='DistroRelease',
                               dbName='distrorelease')

    releases = MultipleJoin('SourcePackageRelease', joinColumn='sourcepackage')


class SourcePackageInDistroSet(object):
    """A Set of SourcePackages in a given DistroRelease"""
    implements(ISourcePackageInDistroSet)
    def __init__(self, distrorelease):
        """Take the distrorelease when it makes part of the context"""
        self.distrorelease = distrorelease
        self.title = 'Source Packages in: ' + distrorelease.title

    def findPackagesByName(self, pattern, fti=False):
        srcutil = getUtility(ISourcePackageSet)
        return srcutil.findByNameInDistroRelease(self.distrorelease.id,
                                                 pattern, fti)

    def __iter__(self):
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
