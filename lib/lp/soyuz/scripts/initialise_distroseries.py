# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Initialise a distroseries from its parent distroseries."""


__metaclass__ = type
__all__ = [
    'InitialisationError',
    'InitialiseDistroSeries',
    ]

from zope.component import getUtility

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.helpers import ensure_unicode
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.adapters.packagelocation import PackageLocation
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.packagecloner import IPackageCloner
from lp.soyuz.interfaces.packageset import IPackagesetSet
from lp.soyuz.model.packageset import Packageset


class InitialisationError(Exception):
    """Raised when there is an exception during the initialisation process."""


class InitialiseDistroSeries:
    """Copy in all of the parent distroseries's configuration. This
    includes all configuration for distroseries as well as distroarchseries,
    publishing and all publishing records for sources and binaries.

    Preconditions:
      The distroseries must exist, and be completly unused, with no source
      or binary packages existing, as well as no distroarchseries set up.
      Section and component selections must be empty.

    Outcome:
      The distroarchseries set up in the parent series will be copied.
      The publishing structure will be copied from the parent. All
      PUBLISHED and PENDING packages in the parent will be created in
      this distroseries and its distroarchseriess. All component and section
      selections will be duplicated, as will any permission-related
      structures.

    Note:
      This method will raise a InitialisationError when the pre-conditions
      are not met. After this is run, you still need to construct chroots
      for building, you need to add anything missing wrt. ports etc. This
      method is only meant to give you a basic copy of a parent series in
      order to assist you in preparing a new series of a distribution or
      in the initialisation of a derivative.
    """

    def __init__(
        self, distroseries, arches=(), packagesets=(), rebuild=False):
        # Avoid circular imports
        from lp.registry.model.distroseries import DistroSeries
        self.distroseries = distroseries
        self.parent = self.distroseries.parent_series
        self.arches = arches
        self.packagesets = [
            ensure_unicode(packageset) for packageset in packagesets]
        self.rebuild = rebuild
        self._store = IMasterStore(DistroSeries)

    def check(self):
        if self.parent is None:
            raise InitialisationError("Parent series required.")
        self._checkBuilds()
        self._checkQueue()
        self._checkSeries()

    def _checkBuilds(self):
        """Assert there are no pending builds for parent series.

        Only cares about the RELEASE pocket, which is the only one inherited
        via initialiseFromParent method.
        """
        # only the RELEASE pocket is inherited, so we only check
        # pending build records for it.
        pending_builds = self.parent.getBuildRecords(
            BuildStatus.NEEDSBUILD, pocket=PackagePublishingPocket.RELEASE)

        if pending_builds.any():
            raise InitialisationError("Parent series has pending builds.")

    def _checkQueue(self):
        """Assert upload queue is empty on parent series.

        Only cares about the RELEASE pocket, which is the only one inherited
        via initialiseFromParent method.
        """
        # only the RELEASE pocket is inherited, so we only check
        # queue items for it.
        for queue in (
            PackageUploadStatus.NEW, PackageUploadStatus.ACCEPTED,
            PackageUploadStatus.UNAPPROVED):
            items = self.parent.getQueueItems(
                queue, pocket=PackagePublishingPocket.RELEASE)
            if items:
                raise InitialisationError(
                    "Parent series queues are not empty.")

    def _checkSeries(self):
        sources = self.distroseries.getAllPublishedSources()
        error = (
            "Can not copy distroarchseries from parent, there are "
            "already distroarchseries(s) initialised for this series.")
        if bool(sources):
            raise InitialisationError(error)
        binaries = self.distroseries.getAllPublishedBinaries()
        if bool(binaries):
            raise InitialisationError(error)
        if bool(self.distroseries.architectures):
            raise InitialisationError(error)
        if bool(self.distroseries.components):
            raise InitialisationError(error)
        if bool(self.distroseries.sections):
            raise InitialisationError(error)

    def initialise(self):
        self._copy_architectures()
        self._copy_packages()
        self._copy_packagesets()

    def _copy_architectures(self):
        include = ''
        if self.arches:
            include = "AND architecturetag IN %s" % sqlvalues(self.arches)
        self._store.execute("""
            INSERT INTO DistroArchSeries
            (distroseries, processorfamily, architecturetag, owner, official)
            SELECT %s, processorfamily, architecturetag, %s, official
            FROM DistroArchSeries WHERE distroseries = %s
            AND enabled = TRUE %s
            """ % (sqlvalues(self.distroseries, self.distroseries.owner,
            self.parent) + (include,)))

        self.distroseries.nominatedarchindep = self.distroseries[
            self.parent.nominatedarchindep.architecturetag]

    def _copy_packages(self):
        # Perform the copies
        self._copy_component_section_and_format_selections()

        # Prepare the list of distroarchseries for which binary packages
        # shall be copied.
        distroarchseries_list = []
        for arch in self.distroseries.architectures:
            if self.arches and (arch.architecturetag not in self.arches):
                continue
            parent_arch = self.parent[arch.architecturetag]
            distroarchseries_list.append((parent_arch, arch))
        # Now copy source and binary packages.
        self._copy_publishing_records(distroarchseries_list)
        self._copy_packaging_links()

    def _copy_publishing_records(self, distroarchseries_list):
        """Copy the publishing records from the parent arch series
        to the given arch series in ourselves.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket in the PRIMARY and DEBUG archives.
        """
        archive_set = getUtility(IArchiveSet)

        spns = []
        # The overhead from looking up each packageset is mitigated by
        # this usually running from a job
        if self.packagesets:
            for pkgsetname in self.packagesets:
                pkgset = getUtility(IPackagesetSet).getByName(
                    pkgsetname, distroseries=self.parent)
                spns += list(pkgset.getSourcesIncluded())

        for archive in self.parent.distribution.all_distro_archives:
            if archive.purpose not in (
                ArchivePurpose.PRIMARY, ArchivePurpose.DEBUG):
                continue

            target_archive = archive_set.getByDistroPurpose(
                self.distroseries.distribution, archive.purpose)
            if archive.purpose is ArchivePurpose.PRIMARY:
                assert target_archive is not None, (
                    "Target archive doesn't exist?")
            origin = PackageLocation(
                archive, self.parent.distribution, self.parent,
                PackagePublishingPocket.RELEASE)
            destination = PackageLocation(
                target_archive, self.distroseries.distribution,
                self.distroseries, PackagePublishingPocket.RELEASE)
            proc_families = None
            if self.rebuild:
                proc_families = [
                    das[1].processorfamily
                    for das in distroarchseries_list]
                distroarchseries_list = ()
            getUtility(IPackageCloner).clonePackages(
                origin, destination, distroarchseries_list,
                proc_families, spns, self.rebuild)

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
            self.parent.id))
        # Copy the section selections
        self._store.execute('''
            INSERT INTO SectionSelection (distroseries, section)
            SELECT %s as distroseries, ss.section AS section
            FROM SectionSelection AS ss WHERE ss.distroseries = %s
            ''' % sqlvalues(self.distroseries.id,
            self.parent.id))
        # Copy the source format selections
        self._store.execute('''
            INSERT INTO SourcePackageFormatSelection (distroseries, format)
            SELECT %s as distroseries, spfs.format AS format
            FROM SourcePackageFormatSelection AS spfs
            WHERE spfs.distroseries = %s
            ''' % sqlvalues(self.distroseries.id,
            self.parent.id))

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

    def _copy_packagesets(self):
        """Copy packagesets from the parent distroseries."""
        packagesets = self._store.find(Packageset, distroseries=self.parent)
        parent_to_child = {}
        # Create the packagesets, and any archivepermissions
        for parent_ps in packagesets:
            if self.packagesets and parent_ps.name not in self.packagesets:
                continue
            child_ps = getUtility(IPackagesetSet).new(
                parent_ps.name, parent_ps.description,
                self.distroseries.owner, distroseries=self.distroseries,
                related_set=parent_ps)
            self._store.execute("""
                INSERT INTO Archivepermission
                (person, permission, archive, packageset, explicit)
                SELECT person, permission, %s, %s, explicit
                FROM Archivepermission WHERE packageset = %s
                """ % sqlvalues(
                    self.distroseries.main_archive, child_ps.id,
                    parent_ps.id))
            parent_to_child[parent_ps] = child_ps
        # Copy the relations between sets, and the contents
        for old_series_ps, new_series_ps in parent_to_child.items():
            old_series_sets = old_series_ps.setsIncluded(
                direct_inclusion=True)
            for old_series_child in old_series_sets:
                new_series_ps.add(parent_to_child[old_series_child])
            new_series_ps.add(old_series_ps.sourcesIncluded(
                direct_inclusion=True))
