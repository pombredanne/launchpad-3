# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Classes to represent source package releases in a distribution."""

__metaclass__ = type

__all__ = [
    'DistributionSourcePackageRelease',
    ]

from lazr.delegates import delegates
from storm.expr import (
    And,
    Desc,
    Join,
    LeftJoin,
    SQL,
    )
from zope.component import getUtility
from zope.interface import implements

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.soyuz.interfaces.archive import MAIN_ARCHIVE_PURPOSES
from lp.soyuz.interfaces.distributionsourcepackagerelease import (
    IDistributionSourcePackageRelease,
    )
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.binarypackagebuild import BinaryPackageBuild
from lp.soyuz.model.binarypackagename import BinaryPackageName
from lp.soyuz.model.binarypackagerelease import BinaryPackageRelease
from lp.soyuz.model.distroseriesbinarypackage import DistroSeriesBinaryPackage
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )


class DistributionSourcePackageRelease:
    """This is a "Magic Distribution Source Package Release". It is not an
    SQLObject, but it represents the concept of a specific source package
    release in the distribution. You can then query it for useful
    information.
    """

    implements(IDistributionSourcePackageRelease)
    delegates(ISourcePackageRelease, context='sourcepackagerelease')

    def __init__(self, distribution, sourcepackagerelease):
        self.distribution = distribution
        self.sourcepackagerelease = sourcepackagerelease

    @property
    def sourcepackage(self):
        """See IDistributionSourcePackageRelease"""
        return self.distribution.getSourcePackage(
            self.sourcepackagerelease.sourcepackagename)

    @property
    def displayname(self):
        """See IDistributionSourcePackageRelease."""
        return '%s in %s' % (self.name, self.distribution.name)

    @property
    def title(self):
        """See IDistributionSourcePackageRelease."""
        return '"%s" %s source package in %s' % (
            self.name, self.version, self.distribution.displayname)

    @property
    def publishing_history(self):
        """See IDistributionSourcePackageRelease."""
        return SourcePackagePublishingHistory.select("""
            DistroSeries.distribution = %s AND
            SourcePackagePublishingHistory.distroseries =
                DistroSeries.id AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.sourcepackagerelease = %s
            """ % sqlvalues(self.distribution,
                            self.distribution.all_distro_archive_ids,
                            self.sourcepackagerelease),
            clauseTables=['DistroSeries'],
            orderBy='-datecreated')

    @property
    def builds(self):
        """See IDistributionSourcePackageRelease."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)

        # Import DistroArchSeries here to avoid circular imports.
        from lp.soyuz.model.distroarchseries import (
            DistroArchSeries)
        from lp.registry.model.distroseries import DistroSeries

        # We want to return all the builds for this distribution that
        # were built for a main archive together with the builds for this
        # distribution that were built for a PPA but have been published
        # in a main archive.
        builds_for_distro_exprs = (
            (BinaryPackageBuild.source_package_release ==
                self.sourcepackagerelease),
            BinaryPackageBuild.distro_arch_series == DistroArchSeries.id,
            DistroArchSeries.distroseries == DistroSeries.id,
            DistroSeries.distribution == self.distribution,
            BinaryPackageBuild.package_build == PackageBuild.id,
            PackageBuild.build_farm_job == BuildFarmJob.id
            )

        # First, get all the builds built in a main archive (this will
        # include new and failed builds.)
        builds_built_in_main_archives = store.find(
            BinaryPackageBuild,
            builds_for_distro_exprs,
            PackageBuild.archive == Archive.id,
            Archive.purpose.is_in(MAIN_ARCHIVE_PURPOSES))

        # Next get all the builds that have a binary published in the
        # main archive... this will include many of those in the above
        # query, but not the new/failed ones. It will also include
        # ppa builds that have been published in main archives.
        builds_published_in_main_archives = store.find(
            BinaryPackageBuild,
            builds_for_distro_exprs,
            BinaryPackageRelease.build == BinaryPackageBuild.id,
            BinaryPackagePublishingHistory.binarypackagerelease ==
                BinaryPackageRelease.id,
            BinaryPackagePublishingHistory.archive == Archive.id,
            Archive.purpose.is_in(MAIN_ARCHIVE_PURPOSES)).config(
                distinct=True)

        return builds_built_in_main_archives.union(
            builds_published_in_main_archives).order_by(
                Desc(BinaryPackageBuild.id))

    @property
    def binary_package_names(self):
        """See IDistributionSourcePackageRelease."""
        return BinaryPackageName.select("""
            BinaryPackageName.id =
                BinaryPackageRelease.binarypackagename AND
            BinaryPackageRelease.build = BinaryPackageBuild.id AND
            BinaryPackageBuild.source_package_release = %s
            """ % sqlvalues(self.sourcepackagerelease.id),
            clauseTables=['BinaryPackageRelease', 'BinaryPackageBuild'],
            orderBy='name',
            distinct=True)

    @property
    def sample_binary_packages(self):
        """See IDistributionSourcePackageRelease."""
        #avoid circular imports.
        from lp.registry.model.distroseries import DistroSeries
        from lp.soyuz.model.distroarchseries import DistroArchSeries
        from lp.soyuz.model.distroseriespackagecache import (
            DistroSeriesPackageCache)
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        archive_ids = list(self.distribution.all_distro_archive_ids)
        result_row = (
            SQL('DISTINCT ON(BinaryPackageName.name) 0 AS ignore'),
            BinaryPackagePublishingHistory, DistroSeriesPackageCache,
            BinaryPackageRelease, BinaryPackageName)
        tables = (
            BinaryPackagePublishingHistory,
            Join(
                DistroArchSeries,
                DistroArchSeries.id ==
                 BinaryPackagePublishingHistory.distroarchseriesID),
            Join(
                DistroSeries,
                DistroArchSeries.distroseriesID == DistroSeries.id),
            Join(
                BinaryPackageRelease,
                BinaryPackageRelease.id ==
                BinaryPackagePublishingHistory.binarypackagereleaseID),
            Join(
                BinaryPackageName,
                BinaryPackageName.id ==
                BinaryPackageRelease.binarypackagenameID),
            Join(
                BinaryPackageBuild,
                BinaryPackageBuild.id == BinaryPackageRelease.buildID),
            LeftJoin(
                DistroSeriesPackageCache,
                And(
                    DistroSeriesPackageCache.distroseries == DistroSeries.id,
                    DistroSeriesPackageCache.archiveID.is_in(archive_ids),
                    DistroSeriesPackageCache.binarypackagename ==
                    BinaryPackageName.id)))

        all_published = store.using(*tables).find(
            result_row,
            DistroSeries.distribution == self.distribution,
            BinaryPackagePublishingHistory.archiveID.is_in(archive_ids),
            BinaryPackageBuild.source_package_release ==
                self.sourcepackagerelease)
        all_published = all_published.order_by(
            BinaryPackageName.name)

        def make_dsb_package(row):
            publishing = row[1]
            package_cache = row[2]
            return DistroSeriesBinaryPackage(
                publishing.distroarchseries.distroseries,
                publishing.binarypackagerelease.binarypackagename,
                package_cache)
        return DecoratedResultSet(all_published, make_dsb_package)
