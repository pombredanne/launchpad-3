# Python imports
from datetime import datetime

# Zope imports
from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, RelatedJoin, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import IDistroArchRelease
from canonical.launchpad.interfaces import IBinaryPackageSet
from canonical.launchpad.database.distribution import Distribution

class DistroArchRelease(SQLBase):

    implements(IDistroArchRelease)
    
    _table = 'DistroArchRelease'

    distrorelease = ForeignKey(dbName='distrorelease',
                               foreignKey='DistroRelease',
                               notNull=True)
    processorfamily = ForeignKey(dbName='processorfamily',
                                 foreignKey='ProcessorFamily',
                                 notNull=True)
    architecturetag = StringCol(dbName='architecturetag',
                              notNull=True)
    owner = ForeignKey(dbName='owner',
                       foreignKey='Person',
                       notNull=True)

    chroot = ForeignKey(dbName='chroot',
                        foreignKey='LibraryFileAlias',
                        notNull=False)

    # useful joins
    packages = RelatedJoin('BinaryPackage', joinColumn='distroarchrelease',
                            intermediateTable='PackagePublishing',
                            otherColumn='binarypackage')

    # for launchpad pages
    def _title(self):
        title = self.architecturetag + ' ('+self.processorfamily.name+') '
        title += 'for ' + self.distrorelease.distribution.displayname
        title += ' ' + self.distrorelease.displayname
        return title
    title = property(_title)


    # useful properties
    def _binarycount(self):
        return len(self.packages)
    binarycount = property(_binarycount)

    def findPackagesByName(self, pattern, fti=False):
        """Search BinaryPackages matching pattern and archtag"""
        binset = getUtility(IBinaryPackageSet)
        return binset.findByNameInDistroRelease(self.distrorelease.id,
                                                pattern,
                                                self.architecturetag,
                                                fti)
        
    def __getitem__(self, name):
        binset = getUtility(IBinaryPackageSet)
        try:
            return binset.getByNameInDistroRelease(\
                                       self.distrorelease.id,
                                       name=name,
                                       archtag=self.architecturetag)[0]
        except IndexError:
            raise KeyError


