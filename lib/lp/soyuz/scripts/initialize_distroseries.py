# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Initialize a distroseries from its parent distroseries."""


__metaclass__ = type
__all__ = [
    'InitializationError',
    'InitializeDistroSeries',
    ]

from operator import methodcaller

import transaction
from zope.component import getUtility

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.helpers import ensure_unicode
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from lp.app.errors import NotFoundError
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.distroseriesparent import IDistroSeriesParentSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database import bulk
from lp.soyuz.adapters.packagelocation import PackageLocation
from lp.soyuz.enums import (
    ArchivePurpose,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.packagecloner import IPackageCloner
from lp.soyuz.interfaces.packageset import (
    IPackagesetSet,
    NoSuchPackageSet,
    )
from lp.soyuz.model.packageset import Packageset
from lp.soyuz.scripts.packagecopier import do_copy
from lp.soyuz.interfaces.archive import CannotCopy


class InitializationError(Exception):
    """Raised when there is an exception during the initialization process."""


class InitializeDistroSeries:
    """Copy in all of the parents distroseries's configuration. This
    includes all configuration for distroseries as well as distroarchseries,
    publishing and all publishing records for sources and binaries.

    Preconditions:
      The distroseries must exist, and be completly unused, with no source
      or binary packages existing, as well as no distroarchseries set up.
      Section and component selections must be empty. It must not have any
      parent series.

    Outcome:
      The distroarchseries set up in the parent series will be copied.
      The publishing structure will be copied from the parents. All
      PUBLISHED and PENDING packages in the parents will be created in
      this distroseries and its distroarchseriess. All component and section
      selections will be duplicated, as will any permission-related
      structures.

    Note:
      This method will raise a InitializationError when the pre-conditions
      are not met. After this is run, you still need to construct chroots
      for building, you need to add anything missing wrt. ports etc. This
      method is only meant to give you a basic copy of parent series in
      order to assist you in preparing a new series of a distribution or
      in the initialization of a derivative.
    """

    def __init__(
        self, distroseries, parents, arches=(), packagesets=(),
        rebuild=False, overlays=(), overlay_pockets=(),
        overlay_components=()):
        # Avoid circular imports
        from lp.registry.model.distroseries import DistroSeries

        self.distroseries = distroseries
        self.parent_ids = [int(id) for id in parents]
        # Load parent objects in bulk...
        parents_bulk = bulk.load(DistroSeries, self.parent_ids)
        # ... sort the parents to match the order in the 'parents' parameter.
        self.parents = sorted(
            parents_bulk,
            key=lambda parent: self.parent_ids.index(parent.id))
        self.arches = arches
        self.packagesets = [
            ensure_unicode(packageset) for packageset in packagesets]
        self.rebuild = rebuild
        self.overlays = overlays
        self.overlay_pockets = overlay_pockets
        self.overlay_components = overlay_components
        self._store = IMasterStore(DistroSeries)

    def check(self):
        if self.distroseries.isDerivedSeries():
            raise InitializationError(
                ("DistroSeries {child.name} has already been initialized"
                 ".").format(
                    child=self.distroseries))
        for parent in self.parents:
            if self.distroseries.distribution.id == parent.distribution.id:
                self._checkBuilds(parent)
            self._checkQueue(parent)
        self._checkSeries()

    def _checkBuilds(self, parent):
        """Assert there are no pending builds for the given parent series.

        Only cares about the RELEASE pocket, which is the only one inherited
        via initializeFromParent method.
        """
        # only the RELEASE pocket is inherited, so we only check
        # pending build records for it.
        pending_builds = parent.getBuildRecords(
            BuildStatus.NEEDSBUILD, pocket=PackagePublishingPocket.RELEASE)

        if pending_builds.any():
            raise InitializationError("Parent series has pending builds.")

    def _checkQueue(self, parent):
        """Assert upload queue is empty on the given parent series.

        Only cares about the RELEASE pocket, which is the only one inherited
        via initializeFromParent method.
        """
        # only the RELEASE pocket is inherited, so we only check
        # queue items for it.
        statuses = [
            PackageUploadStatus.NEW,
            PackageUploadStatus.ACCEPTED,
            PackageUploadStatus.UNAPPROVED,
            ]
        items = parent.getPackageUploads(
            status=statuses, pocket=PackagePublishingPocket.RELEASE)
        if not items.is_empty():
            raise InitializationError(
                "Parent series queues are not empty.")

    def _checkSeries(self):
        error = (
            "Can not copy distroarchseries from parent, there are "
            "already distroarchseries(s) initialized for this series.")
        sources = self.distroseries.getAllPublishedSources()
        binaries = self.distroseries.getAllPublishedBinaries()
        if not all(
            map(methodcaller('is_empty'), (
                sources, binaries, self.distroseries.architectures,
                self.distroseries.sections))):
            raise InitializationError(error)
        if self.distroseries.components:
            raise InitializationError(error)

    def initialize(self):
        self._set_parents()
        self._copy_configuration()
        self._copy_architectures()
        self._copy_packages()
        self._copy_packagesets()
        self._set_initialized()
        transaction.commit()

    def _set_parents(self):
        count = 0
        for parent in self.parents:
            dsp_set = getUtility(IDistroSeriesParentSet)
            if self.overlays and self.overlays[count]:
                pocket = PackagePublishingPocket.__metaclass__.getTermByToken(
                    PackagePublishingPocket,
                    self.overlay_pockets[count]).value
                component_set = getUtility(IComponentSet)
                component = component_set[self.overlay_components[count]]
                dsp_set.new(
                    self.distroseries, parent, initialized=False,
                    is_overlay=True, pocket=pocket, component=component,
                    ordering=count)
            else:
                dsp_set.new(
                    self.distroseries, parent, initialized=False,
                    is_overlay=False, ordering=count)
            count += 1

    def _set_initialized(self):
        dsp_set = getUtility(IDistroSeriesParentSet)
        distroseriesparents = dsp_set.getByDerivedSeries(
            self.distroseries)
        for distroseriesparent in distroseriesparents:
            distroseriesparent.initialized = True

    def _copy_configuration(self):
        self.distroseries.backports_not_automatic = any(
            parent.backports_not_automatic for parent in self.parents)

    def _copy_architectures(self):
        das_filter = ' AND distroseries IN %s ' % (
                sqlvalues(self.parent_ids))
        if self.arches:
            das_filter += ' AND architecturetag IN %s ' % (
                sqlvalues(self.arches))
        self._store.execute("""
            INSERT INTO DistroArchSeries
            (distroseries, processorfamily, architecturetag, owner, official)
            SELECT %s, processorfamily, architecturetag, %s,
                bool_and(official)
            FROM DistroArchSeries WHERE enabled = TRUE %s
            GROUP BY processorfamily, architecturetag
            """ % (sqlvalues(self.distroseries, self.distroseries.owner)
            + (das_filter, )))
        self._store.flush()
        # Take nominatedarchindep from the first parent.
        self.distroseries.nominatedarchindep = self.distroseries[
            self.parents[0].nominatedarchindep.architecturetag]

    def _copy_packages(self):
        # Perform the copies
        self._copy_component_section_and_format_selections()

        # Prepare the lists of distroarchseries for which binary packages
        # shall be copied.
        distroarchseries_lists = {}
        for parent in self.parents:
            distroarchseries_lists[parent] = []
            for arch in self.distroseries.architectures:
                if self.arches and (arch.architecturetag not in self.arches):
                    continue
                try:
                    parent_arch = parent.getDistroArchSeries(
                        arch.architecturetag)
                except NotFoundError:
                    continue

                distroarchseries_lists[parent].append((parent_arch, arch))
        # Now copy source and binary packages.
        self._copy_publishing_records(distroarchseries_lists)
        self._copy_packaging_links()

    def _copy_publishing_records(self, distroarchseries_lists):
        """Copy the publishing records from the parent arch series
        to the given arch series in ourselves.

        We copy all PENDING and PUBLISHED records as PENDING into our own
        publishing records.

        We copy only the RELEASE pocket in the PRIMARY and DEBUG archives.
        """
        archive_set = getUtility(IArchiveSet)

        spns = []
        # The overhead from looking up each packageset is mitigated by
        # this usually running from a job.
        if self.packagesets:
            for pkgsetid in self.packagesets:
                pkgset = self._store.get(Packageset, int(pkgsetid))
                spns += list(pkgset.getSourcesIncluded())

        for parent in self.parents:
            distroarchseries_list = distroarchseries_lists[parent]
            for archive in parent.distribution.all_distro_archives:
                if archive.purpose not in (
                    ArchivePurpose.PRIMARY, ArchivePurpose.DEBUG):
                    continue

                target_archive = archive_set.getByDistroPurpose(
                    self.distroseries.distribution, archive.purpose)
                if archive.purpose is ArchivePurpose.PRIMARY:
                    assert target_archive is not None, (
                        "Target archive doesn't exist?")

            # If the destination archive is empty, we can use the package
            # cloner because there is no conflict possible.
            if target_archive.getPublishedSources().is_empty():
                origin = PackageLocation(
                    archive, parent.distribution, parent,
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
            else:
                # If the destination archive is *not* empty, we use the
                # package copier to avoid conflicts.

                # There is only one available pocket in an unreleased series.
                pocket = PackagePublishingPocket.RELEASE
                sources = archive.getPublishedSources(
                    distroseries=parent, pocket=pocket, names=spns)
                try:
                    do_copy(
                        sources, target_archive, self.distroseries,
                        pocket, include_binaries=not self.rebuild,
                        check_permissions=False, strict_binaries=False)
                except CannotCopy:
                    pass
                if self.rebuild:
                    proc_families = [
                         das[1].processorfamily
                         for das in distroarchseries_list]
                    getUtility(IPackageCloner).createMissingBuilds(
                         self.distroseries, target_archive,
                         distroarchseries_list, proc_families, self.rebuild)

    def _copy_component_section_and_format_selections(self):
        """Copy the section, component and format selections from the parents
        distro series into this one.
        """
        # Copy the component selections
        self._store.execute('''
            INSERT INTO ComponentSelection (distroseries, component)
            SELECT DISTINCT %s AS distroseries, cs.component AS component
            FROM ComponentSelection AS cs WHERE cs.distroseries IN %s
            ''' % sqlvalues(self.distroseries.id,
            self.parent_ids))
        # Copy the section selections
        self._store.execute('''
            INSERT INTO SectionSelection (distroseries, section)
            SELECT DISTINCT %s as distroseries, ss.section AS section
            FROM SectionSelection AS ss WHERE ss.distroseries IN %s
            ''' % sqlvalues(self.distroseries.id,
            self.parent_ids))
        # Copy the source format selections
        self._store.execute('''
            INSERT INTO SourcePackageFormatSelection (distroseries, format)
            SELECT DISTINCT %s as distroseries, spfs.format AS format
            FROM SourcePackageFormatSelection AS spfs
            WHERE spfs.distroseries IN %s
            ''' % sqlvalues(self.distroseries.id,
            self.parent_ids))

    def _copy_packaging_links(self):
        """Copy the packaging links from the parent series to this one."""
        # We iterate over the parents and copy into the child in
        # sequence to avoid creating duplicates.
        for parent_id in self.parent_ids:
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
                    -- Joining the parent distroseries permits the query to
                    -- build the data set for the series being updated, yet
                    -- results are in fact the data from the original series.
                    JOIN Distroseries ChildSeries
                        ON Packaging.distroseries = %s
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
                            WHERE id = %s
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
                """ % sqlvalues(
                    parent_id, self.distroseries.id, parent_id))

    def _copy_packagesets(self):
        """Copy packagesets from the parent distroseries."""
        # Avoid circular imports.
        from lp.registry.model.distroseries import DistroSeries

        packagesets = self._store.find(
            Packageset, DistroSeries.id.is_in(self.parent_ids))
        parent_to_child = {}
        # Create the packagesets, and any archivepermissions
        parent_distro_ids = [
            parent.distribution.id for parent in self.parents]
        for parent_ps in packagesets:
            # Cross-distro initializations get packagesets owned by the
            # distro owner, otherwise the old owner is preserved.
            if self.packagesets and str(parent_ps.id) not in self.packagesets:
                continue
            packageset_set = getUtility(IPackagesetSet)
            # First, try to fetch an existing packageset with this name.
            try:
                child_ps = packageset_set.getByName(
                    parent_ps.name, self.distroseries)
            except NoSuchPackageSet:
                if self.distroseries.distribution.id in parent_distro_ids:
                    new_owner = parent_ps.owner
                else:
                    new_owner = self.distroseries.owner
                child_ps = getUtility(IPackagesetSet).new(
                    parent_ps.name, parent_ps.description,
                    new_owner, distroseries=self.distroseries,
                    related_set=parent_ps)
            # XXX: 2011-06-15 rvb bug=797599.
            # Copying archivepermissions cross-distro is wrong.
            self._store.execute("""
                INSERT INTO Archivepermission
                (person, permission, archive, packageset, explicit)
                SELECT person, permission, %s, %s, explicit
                FROM Archivepermission WHERE packageset = %s
                """ % sqlvalues(
                    self.distroseries.main_archive, child_ps.id,
                    parent_ps.id))
            parent_to_child[parent_ps] = child_ps
        # Copy the relations between sets, and the contents.
        for old_series_ps, new_series_ps in parent_to_child.items():
            old_series_sets = old_series_ps.setsIncluded(
                direct_inclusion=True)
            for old_series_child in old_series_sets:
                new_series_ps.add(parent_to_child[old_series_child])
            new_series_ps.add(old_series_ps.sourcesIncluded(
                direct_inclusion=True))
