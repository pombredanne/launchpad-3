# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistroArchRelease']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import StringCol, ForeignKey, RelatedJoin
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.lp import dbschema

from canonical.launchpad.interfaces import IDistroArchRelease
from canonical.launchpad.interfaces import IBinaryPackageSet
from canonical.launchpad.database.publishing import PackagePublishing


class DistroArchRelease(SQLBase):

    implements(IDistroArchRelease)

    _table = 'DistroArchRelease'

    distrorelease = ForeignKey(dbName='distrorelease',
                               foreignKey='DistroRelease',
                               notNull=True)

    processorfamily = ForeignKey(dbName='processorfamily',
                                 foreignKey='ProcessorFamily',
                                 notNull=True)

    architecturetag = StringCol(dbName='architecturetag', notNull=True)

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    chroot = ForeignKey(dbName='chroot',
                        foreignKey='LibraryFileAlias',
                        notNull=False)

    packages = RelatedJoin('BinaryPackage', joinColumn='distroarchrelease',
                            intermediateTable='PackagePublishing',
                            otherColumn='binarypackage')

    # for launchpad pages
    def title(self):
        title = self.architecturetag + ' ('+self.processorfamily.name+') '
        title += 'for ' + self.distrorelease.distribution.displayname
        title += ' ' + self.distrorelease.displayname
        return title
    title = property(title)

    def binarycount(self):
        # XXX: Needs system doc test. SteveAlexander 2005-04-24.
        query = ('PackagePublishing.distroarchrelease = %s AND '
                 'PackagePublishing.status = %s'
                 % sqlvalues(
                    self.id, dbschema.PackagePublishingStatus.PUBLISHED
                 ))
        return PackagePublishing.select(query).count()
        #return len(self.packages)
    binarycount = property(binarycount)

    def findPackagesByName(self, pattern, fti=False):
        """Search BinaryPackages matching pattern and archtag"""
        binset = getUtility(IBinaryPackageSet)
        return binset.findByNameInDistroRelease(
            self.distrorelease.id, pattern, self.architecturetag, fti)

    def __getitem__(self, name):
        binset = getUtility(IBinaryPackageSet)
        packages = binset.getByNameInDistroRelease(
            self.distrorelease.id, name=name, archtag=self.architecturetag,
            orderBy='id')

        try:
            return packages[0]
        except IndexError:
            raise KeyError, name

