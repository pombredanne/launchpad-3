# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistroArchRelease']

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    StringCol, ForeignKey, RelatedJoin)

from canonical.database.sqlbase import (
    SQLBase, sqlvalues)

from canonical.lp import dbschema

from canonical.launchpad.interfaces import (
    IDistroArchRelease, IBinaryPackageReleaseSet, IPocketChroot,
    IHasBuildRecords, NotFoundError)

from canonical.launchpad.database.publishing import BinaryPackagePublishing
from canonical.launchpad.database.build import Build

__all__ = [
    'DistroArchRelease',
    'PocketChroot',
    ]


class DistroArchRelease(SQLBase):

    implements(IDistroArchRelease, IHasBuildRecords)

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

    @property
    def title(self):
        """See IDistroArchRelease """
        return '%s for %s (%s)' % (
            self.distrorelease.title, self.architecturetag,
            self.processorfamily.name
            )
    
    @property
    def binarycount(self):
        """See IDistroArchRelease """
        # XXX: Needs system doc test. SteveAlexander 2005-04-24.
        query = ('BinaryPackagePublishing.distroarchrelease = %s AND '
                 'BinaryPackagePublishing.status = %s'
                 % sqlvalues(
                    self.id, dbschema.PackagePublishingStatus.PUBLISHED
                 ))
        return BinaryPackagePublishing.select(query).count()

    @property
    def isNominatedArchIndep(self):
        """See IDistroArchRelease"""
        return (self.distrorelease.nominatedarchindep and
                self.id == self.distrorelease.nominatedarchindep.id)
    
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
            raise NotFoundError(name)

    def getBuildRecords(self, status=None, limit=10):
        """See IHasBuildRecords"""
        # specific status or simply touched.
        if status:
            status_clause = "buildstate=%s" % sqlvalues(status)
        else:
            status_clause = "builder is not NULL"
            
        return Build.select(
            "distroarchrelease=%s AND %s" % (self.id, status_clause),
            limit=limit, orderBy="-datebuilt"
            )


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


