# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['DistroArchRelease',
           'DistroArchReleaseSet',
           'PocketChroot'
           ]

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    BoolCol, IntCol, StringCol, ForeignKey, SQLRelatedJoin, SQLObjectNotFound)

from canonical.database.sqlbase import SQLBase, sqlvalues, quote_like, quote
from canonical.database.constants import DEFAULT
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    IDistroArchRelease, IBinaryPackageReleaseSet, IPocketChroot,
    IHasBuildRecords, IBinaryPackageName, IDistroArchReleaseSet,
    IBuildSet, IPublishing)

from canonical.launchpad.database.binarypackagename import BinaryPackageName
from canonical.launchpad.database.distroarchreleasebinarypackage import (
    DistroArchReleaseBinaryPackage)
from canonical.launchpad.database.publishing import (
    BinaryPackagePublishingHistory)
from canonical.launchpad.database.publishedpackage import PublishedPackage
from canonical.launchpad.database.processor import Processor
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)
from canonical.launchpad.helpers import shortlist
from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingStatus)

class DistroArchRelease(SQLBase):
    implements(IDistroArchRelease, IHasBuildRecords, IPublishing)
    _table = 'DistroArchRelease'
    _defaultOrder = 'id'

    distrorelease = ForeignKey(dbName='distrorelease',
        foreignKey='DistroRelease', notNull=True)
    processorfamily = ForeignKey(dbName='processorfamily',
        foreignKey='ProcessorFamily', notNull=True)
    architecturetag = StringCol(notNull=True)
    official = BoolCol(notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    package_count = IntCol(notNull=True, default=DEFAULT)

    packages = SQLRelatedJoin('BinaryPackageRelease',
        joinColumn='distroarchrelease',
        intermediateTable='BinaryPackagePublishing',
        otherColumn='binarypackagerelease')

    def __getitem__(self, name):
        return self.getBinaryPackage(name)

    @property
    def default_processor(self):
        """See IDistroArchRelease"""
        # XXX cprov 20050831
        # I could possibly be better designed, let's think about it in
        # the future. Pick the first processor we found for this
        # distroarchrelease.processorfamily. The data model should
        # change to have a default processor for a processorfamily
        return self.processors[0]

    @property
    def processors(self):
        """See IDistroArchRelease"""
        return Processor.selectBy(family=self.processorfamily, orderBy='id')

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
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.archive = %s AND
            BinaryPackagePublishingHistory.status = %s AND
            BinaryPackagePublishingHistory.pocket = %s
            """ % sqlvalues(
                    self,
                    self.main_archive,
                    PackagePublishingStatus.PUBLISHED,
                    PackagePublishingPocket.RELEASE
                 )
        self.package_count = BinaryPackagePublishingHistory.select(
            query).count()

    @property
    def isNominatedArchIndep(self):
        """See IDistroArchRelease"""
        return (self.distrorelease.nominatedarchindep and
                self.id == self.distrorelease.nominatedarchindep.id)

    def getPocketChroot(self, pocket=None):
        """See IDistroArchRelease"""
        if not pocket:
            pocket = PackagePublishingPocket.RELEASE

        pchroot = PocketChroot.selectOneBy(distroarchrelease=self,
                                           pocket=pocket)

        return pchroot

    def getChroot(self, pocket=None, default=None):
        """See IDistroArchRelease"""
        pocket_chroot = self.getPocketChroot(pocket)

        if pocket_chroot is None:
            return default

        return pocket_chroot.chroot

    def addOrUpdateChroot(self, pocket, chroot):
        """See IDistroArchRelease"""
        pocket_chroot = self.getPocketChroot(pocket)

        if pocket_chroot is None:
            return PocketChroot(
                distroarchrelease=self, pocket=pocket, chroot=chroot)
        else:
            pocket_chroot.chroot = chroot

        return pocket_chroot

    def findPackagesByName(self, pattern, fti=False):
        """Search BinaryPackages matching pattern and archtag"""
        binset = getUtility(IBinaryPackageReleaseSet)
        return binset.findByNameInDistroRelease(
            self.distrorelease, pattern, self.architecturetag, fti)

    def searchBinaryPackages(self, text):
        """See IDistroArchRelease."""
        bprs = BinaryPackageRelease.select("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.archive = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
            BinaryPackagePublishingHistory.status != %s AND
            BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            (BinaryPackageRelease.fti @@ ftq(%s) OR
             BinaryPackageName.name ILIKE '%%' || %s || '%%')
            """ % (quote(self),
                   quote(self.main_archive),
                   quote(PackagePublishingStatus.REMOVED),
                   quote(text),
                   quote_like(text)),
            selectAlso="""
                rank(BinaryPackageRelease.fti, ftq(%s))
                AS rank""" % sqlvalues(text),
            clauseTables=['BinaryPackagePublishingHistory',
                          'BinaryPackageName'],
            prejoinClauseTables=["BinaryPackageName"],
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

    def getBuildRecords(self, status=None, name=None, pocket=None):
        """See IHasBuildRecords"""
        # use facility provided by IBuildSet to retrieve the records
        return getUtility(IBuildSet).getBuildsByArchIds(
            [self.id], status, name, pocket)

    def getReleasedPackages(self, binary_name, pocket=None,
                            include_pending=False, exclude_pocket=None):
        """See IDistroArchRelease."""
        queries = []

        if not IBinaryPackageName.providedBy(binary_name):
            binary_name = BinaryPackageName.byName(binary_name)

        queries.append("""
        binarypackagerelease=binarypackagerelease.id AND
        binarypackagerelease.binarypackagename=%s AND
        distroarchrelease=%s AND
        archive = %s
        """ % sqlvalues(binary_name, self, self.main_archive))

        if pocket is not None:
            queries.append("pocket=%s" % sqlvalues(pocket.value))

        if exclude_pocket is not None:
            queries.append("pocket!=%s" % sqlvalues(exclude_pocket.value))

        if include_pending:
            queries.append("status in (%s, %s)" % sqlvalues(
                PackagePublishingStatus.PUBLISHED,
                PackagePublishingStatus.PENDING))
        else:
            queries.append("status=%s" % sqlvalues(
                PackagePublishingStatus.PUBLISHED))

        published = BinaryPackagePublishingHistory.select(
            " AND ".join(queries),
            clauseTables = ['BinaryPackageRelease'])

        return shortlist(published)

    def findDepCandidateByName(self, name):
        """See IPublishedSet."""
        return PublishedPackage.selectFirstBy(
            binarypackagename=name, distroarchrelease=self,
            packagepublishingstatus=PackagePublishingStatus.PUBLISHED,
            orderBy=['-id'])

    def getPendingPublications(self, pocket, is_careful):
        """See IPublishing."""
        queries = ["distroarchrelease=%s" % sqlvalues(self)]

        target_status = [PackagePublishingStatus.PENDING]
        if is_careful:
            target_status.append(PackagePublishingStatus.PUBLISHED)
        queries.append("status IN %s" % sqlvalues(target_status))

        # restrict to a specific pocket.
        queries.append('pocket = %s' % sqlvalues(pocket))

        # exclude RELEASE pocket if the distrorelease was already released,
        # since it should not change.
        if not self.distrorelease.isUnstable():
            queries.append(
            'pocket != %s' % sqlvalues(PackagePublishingPocket.RELEASE))

        publications = BinaryPackagePublishingHistory.select(
                    " AND ".join(queries), orderBy=["-id"])

        return publications

    def publish(self, diskpool, log, pocket, is_careful=False):
        """See IPublishing."""
        # XXX: this method shares exactly the same pattern as
        # DistroRelease.publish(); they could be factored if API was
        # provided to return the correct publishing entries.
        #    -- kiko, 2006-08-23
        log.debug("Attempting to publish pending binaries for %s"
              % self.architecturetag)

        dirty_pockets = set()

        for bpph in self.getPendingPublications(pocket, is_careful):
            if not is_careful and self.distrorelease.checkLegalPocket(
                bpph, log):
                continue
            bpph.publish(diskpool, log)
            dirty_pockets.add((self.distrorelease.name, bpph.pocket))

        return dirty_pockets

    @property
    def main_archive(self):
        return self.distrorelease.distribution.main_archive


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

    pocket = EnumCol(schema=PackagePublishingPocket,
                     default=PackagePublishingPocket.RELEASE,
                     notNull=True)

    chroot = ForeignKey(dbName='chroot', foreignKey='LibraryFileAlias')

