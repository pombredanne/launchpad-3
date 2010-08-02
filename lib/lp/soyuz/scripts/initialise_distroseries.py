# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Initialise a distroseries from its parent distroseries."""


__metaclass__ = type
__all__ = [
    'InitialiseDistroSeries',
    'ParentSeriesRequired',
    'PendingBuilds',
    'QueueNotEmpty',
    'SeriesAlreadyInUse',
    ]

from canonical.database.sqlbase import (
    cursor, flush_database_caches, flush_database_updates, quote_like,
    quote, SQLBase, sqlvalues)

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.queue import PackageUploadStatus
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory, SourcePackagePublishingHistory)


class PendingBuilds(Exception):
    """Raised when the parent distroseries has pending builds."""


class QueueNotEmpty(Exception):
    """Raised when the parent distroseries has items in its queues."""


class ParentSeriesRequired(Exception):
    """Raised when the distroseries does not have a parent series set."""


class SeriesAlreadyInUse(Exception):
    """Raised when the distroseries already contains things."""


class InitialiseDistroSeries:
    def __init__(self, distroseries):
        self.distroseries = distroseries
        self._check()

    def _check(self):
        if self.distroseries.parent_series is None:
            raise ParentSeriesRequired
        self._checkBuilds()
        self._checkQueue()
        self._checkSeries()

    def _checkBuilds(self):
        """Assert there are no pending builds for parent series.

        Only cares about the RELEASE pocket, which is the only one inherited
        via initialiseFromParent method.
        """
        parentseries = self.distroseries.parent_series

        # only the RELEASE pocket is inherited, so we only check
        # pending build records for it.
        pending_builds = parentseries.getBuildRecords(
            BuildStatus.NEEDSBUILD, pocket=PackagePublishingPocket.RELEASE)

        if pending_builds.count():
            raise PendingBuilds

    def _checkQueue(self):
        """Assert upload queue is empty on parent series.

        Only cares about the RELEASE pocket, which is the only one inherited
        via initialiseFromParent method.
        """
        parentseries = self.distroseries.parent_series

        # only the RELEASE pocket is inherited, so we only check
        # queue items for it.
        for queue in (
            PackageUploadStatus.NEW, PackageUploadStatus.ACCEPTED,
            PackageUploadStatus.UNAPPROVED):
            items = parentseries.getQueueItems(
                queue, pocket=PackagePublishingPocket.RELEASE)
            if items:
                raise QueueNotEmpty

    def _checkSeries(self):
        sources = self.distroseries.getAllPublishedSources()
        if sources.count():
            raise SeriesAlreadyInUse
        binaries = self.distroseries.getAllPublishedBinaries()
        if binaries.count():
            raise SeriesAlreadyInUse
        if self.distroseries.architectures.count():
            raise SeriesAlreadyInUse
        if self.distroseries.components.count():
            raise SeriesAlreadyInUse
        if self.distroseries.sections.count():
            raise SeriesAlreadyInUse

    def initialise(self):
        """See `IDistroSeries`."""
        # MAINTAINER: dsilvers: 20051031
        # Here we go underneath the SQLObject caching layers in order to
        # generate what will potentially be tens of thousands of rows
        # in various tables. Thus we flush pending updates from the SQLObject
        # layer, perform our work directly in the transaction and then throw
        # the rest of the SQLObject cache away to make sure it hasn't cached
        # anything that is no longer true.

        # Prepare for everything by flushing updates to the database.
        flush_database_updates()
        cur = cursor()

        # Perform the copies
        self._copy_component_section_and_format_selections(cur)

        # Prepare the list of distroarchseries for which binary packages
        # shall be copied.
        distroarchseries_list = []
        for arch in self.architectures:
            parent_arch = self.parent_series[arch.architecturetag]
            distroarchseries_list.append((parent_arch, arch))
        # Now copy source and binary packages.
        self._copy_publishing_records(distroarchseries_list)
        self._copy_lucille_config(cur)
        self._copy_packaging_links(cur)

        # Finally, flush the caches because we've altered stuff behind the
        # back of sqlobject.
        flush_database_caches()

    def _copy_lucille_config(self, cur):
        """Copy all lucille related configuration from our parent series."""
        cur.execute('''
            UPDATE DistroSeries SET lucilleconfig=(
                SELECT pdr.lucilleconfig FROM DistroSeries AS pdr
                WHERE pdr.id = %s)
            WHERE id = %s
            ''' % sqlvalues(self.parent_series.id, self.id))

    def _copy_publishing_records(self, distroarchseries_list):
        """Copy the publishing records from the parent arch series
        to the given arch series in ourselves.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket in the PRIMARY and PARTNER
        archives.
        """
        archive_set = getUtility(IArchiveSet)

        for archive in self.parent_series.distribution.all_distro_archives:
            # We only want to copy PRIMARY and PARTNER archives.
            if archive.purpose not in MAIN_ARCHIVE_PURPOSES:
                continue

            # XXX cprov 20080612: Implicitly creating a PARTNER archive for
            # the destination distroseries is bad. Why are we copying
            # partner to a series in another distribution anyway ?
            # See bug #239807 for further information.
            target_archive = archive_set.getByDistroPurpose(
                self.distribution, archive.purpose)
            if target_archive is None:
                target_archive = archive_set.new(
                    distribution=self.distribution, purpose=archive.purpose,
                    owner=self.distribution.owner)

            origin = PackageLocation(
                archive, self.parent_series.distribution, self.parent_series,
                PackagePublishingPocket.RELEASE)
            destination = PackageLocation(
                target_archive, self.distribution, self,
                PackagePublishingPocket.RELEASE)
            clone_packages(origin, destination, distroarchseries_list)

    def _copy_component_section_and_format_selections(self, cur):
        """Copy the section, component and format selections from the parent
        distro series into this one.
        """
        # Copy the component selections
        cur.execute('''
            INSERT INTO ComponentSelection (distroseries, component)
            SELECT %s AS distroseries, cs.component AS component
            FROM ComponentSelection AS cs WHERE cs.distroseries = %s
            ''' % sqlvalues(self.id, self.parent_series.id))
        # Copy the section selections
        cur.execute('''
            INSERT INTO SectionSelection (distroseries, section)
            SELECT %s as distroseries, ss.section AS section
            FROM SectionSelection AS ss WHERE ss.distroseries = %s
            ''' % sqlvalues(self.id, self.parent_series.id))
        # Copy the source format selections
        cur.execute('''
            INSERT INTO SourcePackageFormatSelection (distroseries, format)
            SELECT %s as distroseries, spfs.format AS format
            FROM SourcePackageFormatSelection AS spfs
            WHERE spfs.distroseries = %s
            ''' % sqlvalues(self.id, self.parent_series.id))

    def _copy_packaging_links(self, cur):
        """Copy the packaging links from the parent series to this one."""
        cur.execute("""
            INSERT INTO
                Packaging(
                    distroseries, sourcepackagename, productseries,
                    packaging, owner)
            SELECT
                ChildSeries.id,
                Packaging.sourcepackagename,
                Packaging.productseries,
                Packaging.packaging,
                Packaging.owner
            FROM
                Packaging
                -- Joining the parent distroseries permits the query to build
                -- the data set for the series being updated, yet results are
                -- in fact the data from the original series.
                JOIN Distroseries ChildSeries
                    ON Packaging.distroseries = ChildSeries.parent_series
            WHERE
                -- Select only the packaging links that are in the parent
                -- that are not in the child.
                ChildSeries.id = %s
                AND Packaging.sourcepackagename in (
                    SELECT sourcepackagename
                    FROM Packaging
                    WHERE distroseries in (
                        SELECT id
                        FROM Distroseries
                        WHERE id = ChildSeries.parent_series
                        )
                    EXCEPT
                    SELECT sourcepackagename
                    FROM Packaging
                    WHERE distroseries in (
                        SELECT id
                        FROM Distroseries
                        WHERE id = ChildSeries.id
                        )
                    )
            """ % self.id)

def copy_architectures(distroseries):
    """Overlap SQLObject and copy architecture from the parent.

    Also set the nominatedarchindep properly in target.
    """
    assert distroseries.architectures.count() is 0, (
        "Can not copy distroarchseries from parent, there are already "
        "distroarchseries(s) initialised for this series.")
    flush_database_updates()
    cur = cursor()
    cur.execute("""
    INSERT INTO DistroArchSeries
          (distroseries, processorfamily, architecturetag, owner, official)
    SELECT %s, processorfamily, architecturetag, %s, official
    FROM DistroArchSeries WHERE distroseries = %s
    """ % sqlvalues(distroseries, distroseries.owner,
                    distroseries.parent_series))
    flush_database_caches()

    distroseries.nominatedarchindep = distroseries[
        distroseries.parent_series.nominatedarchindep.architecturetag]


