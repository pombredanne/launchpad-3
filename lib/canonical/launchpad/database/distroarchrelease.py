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

from canonical.launchpad.interfaces import (
    IDistroArchRelease, IBinaryPackageReleaseSet, IPocketChroot,
    IHasBuildRecords, IBinaryPackageName, IDistroArchReleaseSet,
    IBuildSet, IBinaryPackageNameSet, IPublishing)

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
    EnumCol, PackagePublishingPocket, PackagePublishingStatus)

class DistroArchRelease(SQLBase):
    implements(IDistroArchRelease, IHasBuildRecords, IPublishing)
    _table = 'DistroArchRelease'

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
            BinaryPackagePublishingHistory.status = %s AND
            BinaryPackagePublishingHistory.pocket = %s
            """ % sqlvalues(
                    self,
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
            self.distrorelease.id, pattern, self.architecturetag, fti)

    def searchBinaryPackages(self, text):
        """See IDistroArchRelease."""
        bprs = BinaryPackageRelease.select("""
            BinaryPackagePublishingHistory.distroarchrelease = %s AND
            BinaryPackagePublishingHistory.binarypackagerelease =
                BinaryPackageRelease.id AND
             BinaryPackageRelease.binarypackagename =
                BinaryPackageName.id AND
            (BinaryPackageRelease.fti @@ ftq(%s) OR
             BinaryPackageName.name ILIKE '%%' || %s || '%%')
            """ % (quote(self.id), quote(text), quote_like(text)),
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
        return getUtility(IBuildSet).getBuildsByArchIds([self.id], status,
                                                        name, pocket)

    def getReleasedPackages(self, binary_name, pocket=None,
                            include_pending=False, exclude_pocket=None):
        """See IDistroArchRelease."""
        queries = []

        if not IBinaryPackageName.providedBy(binary_name):
            binname_set = getUtility(IBinaryPackageNameSet)
            binary_name = binname_set.getOrCreateByName(binary_name)

        queries.append("""
        binarypackagerelease=binarypackagerelease.id AND
        binarypackagerelease.binarypackagename=%s AND
        distroarchrelease=%s
        """ % sqlvalues(binary_name.id, self.id))

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

    def publish(self, diskpool, log, careful=False, dirty_pockets=None):
        """See IPublishing."""
        log.debug("Attempting to publish pending binaries for %s"
              % self.architecturetag)

        queries = ["distroarchrelease=%s" % sqlvalues(self)]

        target_status = [PackagePublishingStatus.PENDING]
        if careful:
            target_status.append(PackagePublishingStatus.PUBLISHED)
        queries.append("status in %s" % sqlvalues(target_status))

        is_unstable = self.distrorelease.isUnstable()
        pubs = BinaryPackagePublishingHistory.select(
            " AND ".join(queries), orderBy=["-id"])
        for bpph in pubs:
            if not careful:
                # If we're not republishing, we want to make sure that
                # we're not publishing packages into the wrong pocket.
                # Unfortunately for careful mode that can't hold true
                # because we indeed need to republish everything.
                # XXX: untested -- kiko, 2006-08-23
                if (is_unstable and
                    bpph.pocket != PackagePublishingPocket.RELEASE):
                    log.error("Tried to publish %s (%s) into a non-release "
                              "pocket on unstable release %s, skipping" %
                              (bpph.displayname, bpph.id, self.displayname))
                    continue
                if (not is_unstable and
                    bpph.pocket == PackagePublishingPocket.RELEASE):
                    log.error("Tried to publish %s (%s) into release pocket "
                              "on stable release %s, skipping" %
                              (bpph.displayname, bpph.id, self.displayname))
                    continue
            bpph.publish(diskpool, log)

            if dirty_pockets is not None:
                name = self.distrorelease.name
                release_pockets = dirty_pockets.setdefault(name, {})
                release_pockets[bpph.pocket] = True

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
