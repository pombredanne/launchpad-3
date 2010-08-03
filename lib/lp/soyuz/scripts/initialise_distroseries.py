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

from zope.component import getUtility
from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR)

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archive import ArchivePurpose, IArchiveSet
from lp.soyuz.interfaces.queue import PackageUploadStatus


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
        self._store = getUtility(
            IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
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
        self._copy_architectures()
        self._copy_packages()

    def _copy_architectures(self):
        self._store.execute("""
            INSERT INTO DistroArchSeries
            (distroseries, processorfamily, architecturetag, owner, official)
            SELECT %s, processorfamily, architecturetag, %s, official
            FROM DistroArchSeries WHERE distroseries = %s
            """ % sqlvalues(self.distroseries, self.distroseries.owner,
            self.distroseries.parent_series))

        self.distroseries.nominatedarchindep = self.distroseries[
            self.distroseries.parent_series.nominatedarchindep.architecturetag]

    def _copy_packages(self):
        # Perform the copies
        self._copy_component_section_and_format_selections()

        # Prepare the list of distroarchseries for which binary packages
        # shall be copied.
        distroarchseries_list = []
        for arch in self.distroseries.architectures:
            parent_arch = self.distroseries.parent_series[arch.architecturetag]
            distroarchseries_list.append((parent_arch, arch))
        # Now copy source and binary packages.
        self._copy_publishing_records(distroarchseries_list)
        self._copy_lucille_config()
        self._copy_packaging_links()

    def _copy_lucille_config(self):
        """Copy all lucille related configuration from our parent series."""
        self._store.execute('''
            UPDATE DistroSeries SET lucilleconfig=(
                SELECT pdr.lucilleconfig FROM DistroSeries AS pdr
                WHERE pdr.id = %s)
            WHERE id = %s
            ''' % sqlvalues(self.distroseries.parent_series.id,
            self.distroseries.id))

    def _copy_publishing_records(self, distroarchseries_list):
        """Copy the publishing records from the parent arch series
        to the given arch series in ourselves.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket in the PRIMARY and PARTNER
        archives.
        """
        archive_set = getUtility(IArchiveSet)
        parent = self.distroseries.parent_series

        for archive in parent.distribution.all_distro_archives:
            if archive.purpose is not ArchivePurpose.PRIMARY:
                continue

            # XXX cprov 20080612: Implicitly creating a PARTNER archive for
            # the destination distroseries is bad. Why are we copying
            # partner to a series in another distribution anyway ?
            # See bug #239807 for further information.
            target_archive = archive_set.getByDistroPurpose(
                self.distroseries.distribution, archive.purpose)
            if target_archive is None:
                target_archive = archive_set.new(
                    distribution=self.distroseries.distribution,
                    purpose=archive.purpose,
                    owner=self.distroseries.distribution.owner)

            origin = PackageLocation(
                archive, parent.distribution, parent,
                PackagePublishingPocket.RELEASE)
            destination = PackageLocation(
                target_archive, self.distroseries.distribution,
                self.distroseries, PackagePublishingPocket.RELEASE)
            clone_packages(origin, destination, distroarchseries_list)

    def _copy_component_section_and_format_selections(self):
        """Copy the section, component and format selections from the parent
        distro series into this one.
        """
        # Copy the component selections
        self._store.execute('''
            INSERT INTO ComponentSelection (distroseries, component)
            SELECT %s AS distroseries, cs.component AS component
            FROM ComponentSelection AS cs WHERE cs.distroseries = %s
            ''' % sqlvalues(self.distroseries.id,
            self.distroseries.parent_series.id))
        # Copy the section selections
        self._store.execute('''
            INSERT INTO SectionSelection (distroseries, section)
            SELECT %s as distroseries, ss.section AS section
            FROM SectionSelection AS ss WHERE ss.distroseries = %s
            ''' % sqlvalues(self.distroseries.id,
            self.distroseries.parent_series.id))
        # Copy the source format selections
        self._store.execute('''
            INSERT INTO SourcePackageFormatSelection (distroseries, format)
            SELECT %s as distroseries, spfs.format AS format
            FROM SourcePackageFormatSelection AS spfs
            WHERE spfs.distroseries = %s
            ''' % sqlvalues(self.distroseries.id,
            self.distroseries.parent_series.id))

    def _copy_packaging_links(self):
        """Copy the packaging links from the parent series to this one."""
        self._store.execute("""
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
            """ % self.distroseries.id)

