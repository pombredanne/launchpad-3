# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistroArchRelease',
           'DistroArchReleaseSet',
           'PocketChroot'
           ]

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    BoolCol, IntCol, StringCol, ForeignKey, RelatedJoin, SQLObjectNotFound)

from canonical.lp import dbschema
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import DEFAULT

from canonical.launchpad.interfaces import (
    IDistroArchRelease, IBinaryPackageReleaseSet, IPocketChroot,
    IHasBuildRecords, IBinaryPackageName, IDistroArchReleaseSet,
    IBuildSet)

from canonical.launchpad.database.binarypackagename import BinaryPackageName
from canonical.launchpad.database.distroarchreleasebinarypackage import (
    DistroArchReleaseBinaryPackage)
from canonical.launchpad.database.publishing import BinaryPackagePublishing
from canonical.launchpad.database.publishedpackage import PublishedPackage
from canonical.launchpad.database.processor import Processor
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.helpers import shortlist


class DistroArchRelease(SQLBase):
    implements(IDistroArchRelease, IHasBuildRecords)
    _table = 'DistroArchRelease'

    distrorelease = ForeignKey(dbName='distrorelease',
        foreignKey='DistroRelease', notNull=True)
    processorfamily = ForeignKey(dbName='processorfamily',
        foreignKey='ProcessorFamily', notNull=True)
    architecturetag = StringCol(notNull=True)
    official = BoolCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    package_count = IntCol(notNull=True, default=DEFAULT)

    packages = RelatedJoin('BinaryPackageRelease',
        joinColumn='distroarchrelease',
        intermediateTable='BinaryPackagePublishing',
        otherColumn='binarypackagerelease')

    def __getitem__(self, name):
        return self.getBinaryPackage(name)

    @property
    def default_processor(self):
        """See IDistroArchRelease"""
        return self.processors[0]

    @property
    def processors(self):
        """See IDistroArchRelease"""
        return Processor.selectBy(familyID=self.processorfamily.id,
                                  orderBy='id')

    @property
    def title(self):
        """See IDistroArchRelease """
        return '%s for %s (%s)' % (
            self.distrorelease.title, self.architecturetag,
            self.processorfamily.name
            )

    @property
    def displayname(self):
        """See IDistroArchRelease."""
        return '%s %s' % (self.distrorelease.name, self.architecturetag)

    def updatePackageCount(self):
        """See IDistroArchRelease """
        query = """
            BinaryPackagePublishing.distroarchrelease = %s AND
            BinaryPackagePublishing.status = %s AND
            BinaryPackagePublishing.pocket = %s
            """ % sqlvalues(
                    self.id,
                    dbschema.PackagePublishingStatus.PUBLISHED,
                    dbschema.PackagePublishingPocket.RELEASE
                 )
        self.package_count = BinaryPackagePublishing.select(query).count()

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

    def searchBinaryPackages(self, text):
        """See IDistroArchRelease."""
        bprs = BinaryPackageRelease.select("""
            BinaryPackagePublishing.distroarchrelease = %s AND
            BinaryPackagePublishing.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackageRelease.fti @@ ftq(%s)
            """ % sqlvalues(self.id, text),
            selectAlso="""
                rank(BinaryPackageRelease.fti, ftq(%s))
                AS rank""" % sqlvalues(text),
            clauseTables=['BinaryPackagePublishing'],
            orderBy=['-rank'],
            distinct=True)
        # import here to avoid circular import problems
        from canonical.launchpad.database import (
            DistroArchReleaseBinaryPackageRelease)
        return [DistroArchReleaseBinaryPackageRelease(
                    distroarchrelease=self,
                    binarypackagerelease=bpr) for bpr in bprs]

    def getBinaryPackage(self, name):
        """See IDistroArchRelease."""
        if not IBinaryPackageName.providedBy(name):
            try:
                name = BinaryPackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return DistroArchReleaseBinaryPackage(
            self, name)

    def getBuildRecords(self, status=None):
        """See IHasBuildRecords"""
        # use facility provided by IBuildSet to retrieve the records
        return getUtility(IBuildSet).getBuildsByArchIds([self.id], status)

    def getReleasedPackages(self, name, pocket=None):
        """See IDistroArchRelease."""
        if not IBinaryPackageName.providedBy(name):
            name = BinaryPackageName.byName(name)
        pocketclause = ""
        if pocket is not None:
            pocketclause = "AND pocket=%s" % sqlvalues(pocket.value)
        published = BinaryPackagePublishing.select((
            """
            distroarchrelease = %s AND
            status = %s AND
            binarypackagerelease = binarypackagerelease.id AND
            binarypackagerelease.binarypackagename = %s
            """ % sqlvalues(self.id,
                            dbschema.PackagePublishingStatus.PUBLISHED,
                            name.id))+pocketclause,
            clauseTables = ['BinaryPackageRelease'])
        return shortlist(published)

    def findDepCandidateByName(self, name):
        """See IPublishedSet."""
        return PublishedPackage.selectOneBy(
            binarypackagename=name, distroarchreleaseID=self.id,
            packagepublishingstatus=dbschema.PackagePublishingStatus.PUBLISHED
            )


class DistroArchReleaseSet:
    """This class is to deal with DistroArchRelease related stuff"""

    implements(IDistroArchReleaseSet)

    def __iter__(self):
        return iter(DistroArchRelease.select())

    def get(self, dar_id):
        """See canonical.launchpad.interfaces.IDistributionSet."""
        return DistroArchRelease.get(dar_id)

    def count(self):
        return DistroArchRelease.select().count()

class PocketChroot(SQLBase):
    implements(IPocketChroot)
    _table = "PocketChroot"

    distroarchrelease = ForeignKey(dbName='distroarchrelease',
                                   foreignKey='DistroArchRelease',
                                   notNull=True)
    pocket = dbschema.EnumCol(schema=dbschema.PackagePublishingPocket,
                              default=dbschema.PackagePublishingPocket.RELEASE,
                              notNull=True)
    chroot = ForeignKey(dbName='chroot',
                        foreignKey='LibraryFileAlias')


