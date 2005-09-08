# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistroArchRelease']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import StringCol, ForeignKey, RelatedJoin
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.lp import dbschema

from canonical.launchpad.interfaces import (
    IDistroArchRelease, IBinaryPackageReleaseSet, IPocketChroot
    )
from canonical.launchpad.database.publishing import BinaryPackagePublishing

__all__ = [
    'DistroArchRelease',
    'PocketChroot',
    ]


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

    packages = RelatedJoin('BinaryPackage', joinColumn='distroarchrelease',
                            intermediateTable='BinaryPackagePublishing',
                            otherColumn='binarypackage')

    # for launchpad pages
    def title(self):
        title = self.distrorelease.distribution.displayname
        title += ' ' + self.distrorelease.displayname
        title += ' for the ' + self.architecturetag
        title += ' ('+self.processorfamily.name+') architecture'
        return title
    title = property(title)

    def binarycount(self):
        # XXX: Needs system doc test. SteveAlexander 2005-04-24.
        query = ('BinaryPackagePublishing.distroarchrelease = %s AND '
                 'BinaryPackagePublishing.status = %s'
                 % sqlvalues(
                    self.id, dbschema.PackagePublishingStatus.PUBLISHED
                 ))
        return BinaryPackagePublishing.select(query).count()
        #return len(self.packages)
    binarycount = property(binarycount)

    def getChroot(self, pocket=None, default=None):
        """See IDistroArchRelease"""
        if not pocket:
            pocket = dbschema.PackagePublishingPocket.RELEASE

        pchroot = PocketChroot.selectOneBy(distroarchreleaseID=self.id,
                                           pocket=pocket)
        if pchroot:
            # return the librarianfilealias of the chroot
            return pchroot.chroot

        return default
        
        
    def findPackagesByName(self, pattern, fti=False):
        """Search BinaryPackages matching pattern and archtag"""
        binset = getUtility(IBinaryPackageReleaseSet)
        return binset.findByNameInDistroRelease(
            self.distrorelease.id, pattern, self.architecturetag, fti)

    def __getitem__(self, name):
        binset = getUtility(IBinaryPackageReleaseSet)
        packages = binset.getByNameInDistroRelease(
            self.distrorelease.id, name=name, archtag=self.architecturetag,
            orderBy='id')

        try:
            return packages[0]
        except IndexError:
            raise KeyError, name


class PocketChroot(SQLBase):
    implements(IPocketChroot)
    _table = "PocketChroot"

    distroarchrelease = ForeignKey(dbName='distroarchrelease',
                                   foreignKey='DistroArchRelease',
                                   notNull=True)

    pocket = dbschema.EnumCol(dbName='pocket',
                              schema=dbschema.PackagePublishingPocket,
                              default=dbschema.PackagePublishingPocket.RELEASE,
                              notNull=True)

    chroot = ForeignKey(dbName='chroot',
                        foreignKey='LibraryFileAlias')


