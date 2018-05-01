# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'DistroArchSeries',
    'PocketChroot'
    ]

from cStringIO import StringIO
import hashlib

from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLObjectNotFound,
    SQLRelatedJoin,
    StringCol,
    )
from storm.locals import (
    Int,
    Join,
    Or,
    Reference,
    )
from storm.store import EmptyResultSet
from zope.component import getUtility
from zope.interface import implementer

from lp.buildmaster.model.processor import Processor
from lp.registry.interfaces.person import validate_public_person
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.constants import DEFAULT
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from lp.services.database.stormexpr import (
    fti_search,
    rank_by_fti,
    )
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.services.webapp.publisher import (
    get_raw_form_value_from_current_request,
    )
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageName
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords
from lp.soyuz.interfaces.distroarchseries import (
    IDistroArchSeries,
    InvalidChrootUploaded,
    IPocketChroot,
    )
from lp.soyuz.interfaces.publishing import active_publishing_status
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease


@implementer(IDistroArchSeries, IHasBuildRecords)
class DistroArchSeries(SQLBase):
    _table = 'DistroArchSeries'
    _defaultOrder = 'id'

    distroseries = ForeignKey(dbName='distroseries',
        foreignKey='DistroSeries', notNull=True)
    processor_id = Int(name='processor', allow_none=False)
    processor = Reference(processor_id, Processor.id)
    architecturetag = StringCol(notNull=True)
    official = BoolCol(notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    package_count = IntCol(notNull=True, default=DEFAULT)
    enabled = BoolCol(notNull=False, default=True)

    packages = SQLRelatedJoin('BinaryPackageRelease',
        joinColumn='distroarchseries',
        intermediateTable='BinaryPackagePublishing',
        otherColumn='binarypackagerelease')

    def __getitem__(self, name):
        return self.getBinaryPackage(name)

    @property
    def title(self):
        """See `IDistroArchSeries`."""
        return '%s for %s (%s)' % (
            self.distroseries.title, self.architecturetag, self.processor.name)

    @property
    def displayname(self):
        """See `IDistroArchSeries`."""
        return '%s %s %s' % (
            self.distroseries.distribution.displayname,
            self.distroseries.displayname, self.architecturetag)

    @property
    def supports_virtualized(self):
        return self.processor.supports_virtualized

    def updatePackageCount(self):
        """See `IDistroArchSeries`."""
        from lp.soyuz.model.publishing import BinaryPackagePublishingHistory

        query = """
            BinaryPackagePublishingHistory.distroarchseries = %s AND
            BinaryPackagePublishingHistory.archive IN %s AND
            BinaryPackagePublishingHistory.status = %s AND
            BinaryPackagePublishingHistory.pocket = %s
            """ % sqlvalues(
                    self,
                    self.distroseries.distribution.all_distro_archive_ids,
                    PackagePublishingStatus.PUBLISHED,
                    PackagePublishingPocket.RELEASE
                 )
        self.package_count = BinaryPackagePublishingHistory.select(
            query).count()

    @property
    def isNominatedArchIndep(self):
        """See `IDistroArchSeries`."""
        return (self.distroseries.nominatedarchindep is not None and
                self.id == self.distroseries.nominatedarchindep.id)

    def getPocketChroot(self):
        """See `IDistroArchSeries`."""
        pchroot = PocketChroot.selectOneBy(distroarchseries=self)
        return pchroot

    def getChroot(self, default=None):
        """See `IDistroArchSeries`."""
        pocket_chroot = self.getPocketChroot()

        if pocket_chroot is None:
            return default

        return pocket_chroot.chroot

    @property
    def chroot_url(self):
        """See `IDistroArchSeries`."""
        chroot = self.getChroot()
        if chroot is None:
            return None
        return chroot.http_url

    def addOrUpdateChroot(self, chroot):
        """See `IDistroArchSeries`."""
        pocket_chroot = self.getPocketChroot()

        if pocket_chroot is None:
            return PocketChroot(distroarchseries=self, chroot=chroot)
        else:
            pocket_chroot.chroot = chroot

        return pocket_chroot

    def setChroot(self, data, sha1sum):
        """See `IDistroArchSeries`."""
        # XXX: StevenK 2013-06-06 bug=1116954: We should not need to refetch
        # the file content from the request, since the passed in one has been
        # wrongly encoded.
        data = get_raw_form_value_from_current_request(data, 'data')
        if isinstance(data, str):
            filecontent = data
        else:
            filecontent = data.read()

        # Due to http://bugs.python.org/issue1349106 launchpadlib sends
        # MIME with \n line endings, which is illegal. lazr.restful
        # parses each ending as \r\n, resulting in a binary that ends
        # with \r getting the last byte chopped off. To cope with this
        # on the server side we try to append \r if the SHA-1 doesn't
        # match.
        content_sha1sum = hashlib.sha1(filecontent).hexdigest()
        if content_sha1sum != sha1sum:
            filecontent += '\r'
            content_sha1sum = hashlib.sha1(filecontent).hexdigest()
        if content_sha1sum != sha1sum:
            raise InvalidChrootUploaded("Chroot upload checksums do not match")

        filename = 'chroot-%s-%s-%s.tar.bz2' % (
            self.distroseries.distribution.name, self.distroseries.name,
            self.architecturetag)
        lfa = getUtility(ILibraryFileAliasSet).create(
            name=filename, size=len(filecontent), file=StringIO(filecontent),
            contentType='application/octet-stream')
        if lfa.content.sha1 != sha1sum:
            raise InvalidChrootUploaded("Chroot upload checksums do not match")
        self.addOrUpdateChroot(lfa)

    def setChrootFromBuild(self, livefsbuild, filename):
        """See `IDistroArchSeries`."""
        self.addOrUpdateChroot(livefsbuild.getFileByName(filename))

    def removeChroot(self):
        """See `IDistroArchSeries`."""
        self.addOrUpdateChroot(None)

    def searchBinaryPackages(self, text):
        """See `IDistroArchSeries`."""
        from lp.soyuz.model.publishing import BinaryPackagePublishingHistory

        origin = [
            BinaryPackageRelease,
            Join(
                BinaryPackagePublishingHistory,
                BinaryPackagePublishingHistory.binarypackagerelease ==
                    BinaryPackageRelease.id),
            Join(
                BinaryPackageName,
                BinaryPackageRelease.binarypackagename ==
                    BinaryPackageName.id)]

        find_spec = [BinaryPackageRelease, BinaryPackageName]
        archives = self.distroseries.distribution.getArchiveIDList()

        clauses = [
            BinaryPackagePublishingHistory.distroarchseries == self,
            BinaryPackagePublishingHistory.archiveID.is_in(archives),
            BinaryPackagePublishingHistory.status.is_in(
                active_publishing_status)]
        order_by = [BinaryPackageName.name]
        if text:
            ranking = rank_by_fti(BinaryPackageRelease, text)
            find_spec.append(ranking)
            clauses.append(
                Or(
                    fti_search(BinaryPackageRelease, text),
                    BinaryPackageName.name.contains_string(text.lower())))
            order_by.insert(0, ranking)
        result = IStore(BinaryPackageName).using(*origin).find(
            tuple(find_spec), *clauses).config(distinct=True).order_by(
                *order_by)

        # import here to avoid circular import problems
        from lp.soyuz.model.distroarchseriesbinarypackagerelease import (
            DistroArchSeriesBinaryPackageRelease)

        # Create a function that will decorate the results, converting
        # them from the find_spec above into DASBPRs.
        def result_to_dasbpr(row):
            return DistroArchSeriesBinaryPackageRelease(
                distroarchseries=self, binarypackagerelease=row[0])

        # Return the decorated result set so the consumer of these
        # results will only see DSPs.
        return DecoratedResultSet(result, result_to_dasbpr)

    def getBinaryPackage(self, name):
        """See `IDistroArchSeries`."""
        from lp.soyuz.model.distroarchseriesbinarypackage import (
            DistroArchSeriesBinaryPackage,
            )
        if not IBinaryPackageName.providedBy(name):
            try:
                name = BinaryPackageName.byName(name)
            except SQLObjectNotFound:
                return None
        return DistroArchSeriesBinaryPackage(
            self, name)

    def getBuildRecords(self, build_state=None, name=None, pocket=None,
                        arch_tag=None, user=None, binary_only=True):
        """See IHasBuildRecords"""
        # Ignore "user", since it would not make any difference to the
        # records returned here (private builds are only in PPA right
        # now).
        # Ignore "binary_only" as for a distro arch series it is only
        # the binaries that are relevant.

        # For consistency we return an empty resultset if arch_tag
        # is provided but doesn't match our architecture.
        if arch_tag is not None and arch_tag != self.architecturetag:
            return EmptyResultSet()

        # Use the facility provided by IBinaryPackageBuildSet to
        # retrieve the records.
        return getUtility(IBinaryPackageBuildSet).getBuildsForDistro(
            self, build_state, name, pocket)

    @property
    def main_archive(self):
        return self.distroseries.distribution.main_archive


@implementer(IPocketChroot)
class PocketChroot(SQLBase):
    _table = "PocketChroot"

    distroarchseries = ForeignKey(
        dbName='distroarchseries', foreignKey='DistroArchSeries', notNull=True)

    pocket = EnumCol(
        schema=PackagePublishingPocket,
        default=PackagePublishingPocket.RELEASE, notNull=True)

    chroot = ForeignKey(dbName='chroot', foreignKey='LibraryFileAlias')
