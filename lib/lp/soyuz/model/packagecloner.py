# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Logic for bulk copying of source/binary publishing history data."""

__metaclass__ = type

__all__ = [
    'PackageCloner',
    'clone_packages',
    ]


from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import quote, sqlvalues
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.interfaces.packagecloner import IPackageCloner
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)


def clone_packages(origin, destination, distroarchseries_list=None):
    """Copies packages from origin to destination package location.

    Binary packages are only copied for the `DistroArchSeries` pairs
    specified.

    This function is meant to simplify the utilization of the package
    cloning functionality.

    @type origin: PackageLocation
    @param origin: the location from which packages are to be copied.
    @type destination: PackageLocation
    @param destination: the location to which the data is to be copied.
    @type distroarchseries_list: list of pairs of (origin, destination)
        distroarchseries instances.
    @param distroarchseries_list: the binary packages will be copied
        for the distroarchseries pairs specified (if any).
    """
    pkg_cloner = getUtility(IPackageCloner)
    pkg_cloner.clonePackages(origin, destination, distroarchseries_list)


class PackageCloner:
    """Used for copying of various publishing history data across archives.
    """

    implements(IPackageCloner)

    def clonePackages(self, origin, destination, distroarchseries_list=None):
        """Copies packages from origin to destination package location.

        Binary packages are only copied for the `DistroArchSeries` pairs
        specified.

        @type origin: PackageLocation
        @param origin: the location from which packages are to be copied.
        @type destination: PackageLocation
        @param destination: the location to which the data is to be copied.
        @type distroarchseries_list: list of pairs of (origin, destination)
            distroarchseries instances.
        @param distroarchseries_list: the binary packages will be copied
            for the distroarchseries pairs specified (if any).
        """
        # First clone the source packages.
        self._clone_source_packages(origin, destination)

        # Are we also supposed to clone binary packages from origin to
        # destination distroarchseries pairs?
        if distroarchseries_list is not None:
            for (origin_das, destination_das) in distroarchseries_list:
                self._clone_binary_packages(
                    origin, destination, origin_das, destination_das)


    def _clone_binary_packages(self, origin, destination, origin_das,
                              destination_das):
        """Copy binary publishing data from origin to destination.

        @type origin: PackageLocation
        @param origin: the location from which binary publishing
            records are to be copied.
        @type destination: PackageLocation
        @param destination: the location to which the data is
            to be copied.
        @type origin_das: DistroArchSeries
        @param origin_das: the DistroArchSeries from which to copy
            binary packages
        @type destination_das: DistroArchSeries
        @param destination_das: the DistroArchSeries to which to copy
            binary packages
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        store.execute('''
            INSERT INTO SecureBinaryPackagePublishingHistory (
                binarypackagerelease, distroarchseries, status,
                component, section, priority, archive, datecreated,
                datepublished, pocket, embargo)
            SELECT bpph.binarypackagerelease, %s as distroarchseries,
                   bpph.status, bpph.component, bpph.section, bpph.priority,
                   %s as archive, %s as datecreated, %s as datepublished,
                   %s as pocket, false as embargo
            FROM BinaryPackagePublishingHistory AS bpph
            WHERE bpph.distroarchseries = %s AND bpph.status in (%s, %s)
            AND
                bpph.pocket = %s and bpph.archive = %s
            ''' % sqlvalues(
                destination_das, destination.archive, UTC_NOW, UTC_NOW,
                destination.pocket, origin_das,
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED,
                origin.pocket, origin.archive))

    def mergeCopy(self, origin, destination):
        """Please see `IPackageCloner`."""
        # Calculate the package set delta in order to find packages that are
        # obsolete or missing in the target archive.
        self.packageSetDiff(origin, destination)

        # Now copy the fresher or new packages.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        store.execute("""
            INSERT INTO SecureSourcePackagePublishingHistory (
                sourcepackagerelease, distroseries, status, component,
                section, archive, datecreated, datepublished, pocket,
                embargo)
            SELECT
                mcd.s_sourcepackagerelease AS sourcepackagerelease,
                %s AS distroseries, mcd.s_status AS status,
                mcd.s_component AS component, mcd.s_section AS section,
                %s AS archive, %s AS datecreated, %s AS datepublished,
                %s AS pocket, False AS embargo
            FROM tmp_merge_copy_data mcd
            WHERE mcd.obsoleted = True OR mcd.missing = True
            """ % sqlvalues(
                destination.distroseries, destination.archive, UTC_NOW,
                UTC_NOW, destination.pocket))

        # Finally set the publishing status for the packages obsoleted in the
        # target archive accordingly (i.e make them superseded).
        store.execute("""
            UPDATE securesourcepackagepublishinghistory secsrc
            SET
                status = %s,
                datesuperseded = %s,
                supersededby = mcd.s_sourcepackagerelease
            FROM
                tmp_merge_copy_data mcd
            WHERE
                secsrc.id = mcd.t_sspph AND mcd.obsoleted = True
            """ % sqlvalues(
                PackagePublishingStatus.SUPERSEDED, UTC_NOW))

    def _compute_packageset_delta(self, origin):
        """Given a source/target archive find obsolete or missing packages.

        This means finding out which packages in a given source archive are
        fresher or new with respect to a target archive.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        # The query below will find all packages in the source archive that
        # are fresher than their counterparts in the target archive.
        find_newer_packages = """
            UPDATE tmp_merge_copy_data mcd SET
                s_sspph = secsrc.id,
                s_sourcepackagerelease = spr.id,
                s_version = spr.version,
                obsoleted = True,
                s_status = secsrc.status,
                s_component = secsrc.component,
                s_section = secsrc.section
            FROM
                securesourcepackagepublishinghistory secsrc,
                sourcepackagerelease spr, sourcepackagename spn
            WHERE
                secsrc.archive = %s AND secsrc.status IN (%s, %s) AND
                secsrc.distroseries = %s AND secsrc.pocket = %s AND
                secsrc.sourcepackagerelease = spr.id AND
                spr.sourcepackagename = spn.id AND
                spn.name = mcd.sourcepackagename AND
                debversion_sort_key(spr.version) > debversion_sort_key(mcd.t_version)
        """ % sqlvalues(
                origin.archive,
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED,
                origin.distroseries, origin.pocket)

        if origin.component is not None:
            find_newer_packages += (
                " AND secsrc.component = %s" % quote(origin.component))
        store.execute(find_newer_packages)

        # Now find the packages that exist in the source archive but *not* in
        # the target archive.
        find_origin_only_packages = """
            INSERT INTO tmp_merge_copy_data (
                s_sspph, s_sourcepackagerelease, sourcepackagename, s_version,
                missing, s_status, s_component, s_section)
            SELECT
                secsrc.id AS s_sspph,
                secsrc.sourcepackagerelease AS s_sourcepackagerelease,
                spn.name AS sourcepackagename, spr.version AS s_version,
                True AS missing, secsrc.status AS s_status,
                secsrc.component AS s_component, secsrc.section AS s_section
            FROM
                securesourcepackagepublishinghistory secsrc,
                sourcepackagerelease spr, sourcepackagename spn
            WHERE
                secsrc.archive = %s AND secsrc.status IN (%s, %s) AND
                secsrc.distroseries = %s AND secsrc.pocket = %s AND
                secsrc.sourcepackagerelease = spr.id AND
                spr.sourcepackagename = spn.id AND
                spn.name NOT IN (
                    SELECT sourcepackagename FROM tmp_merge_copy_data)
        """ % sqlvalues(
                origin.archive,
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED,
                origin.distroseries, origin.pocket)
        
        if origin.component is not None:
            find_origin_only_packages += (
                " AND secsrc.component = %s" % quote(origin.component))
        store.execute(find_origin_only_packages)

    def _init_packageset_delta(self, destination):
        """Set up a temp table with data about target archive packages.

        This is a first step in finding out which packages in a given source
        archive are fresher or new with respect to a target archive.

        Merge copying of packages is one of the use cases that requires such a
        package set diff capability.

        In order to find fresher or new packages we first set up a temporary
        table that lists what packages exist in the target archive
        (additionally considering the distroseries, pocket and component).
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        # Use a temporary table to hold the data needed for the package set
        # delta computation. This will prevent multiple, parallel delta
        # calculations from interfering with each other.
        store.execute("""
            CREATE TEMP TABLE tmp_merge_copy_data (
                -- Source archive package data, only set for packages that
                -- will be copied.
                s_sspph integer,
                s_sourcepackagerelease integer,
                s_version text,
                s_status integer,
                s_component integer,
                s_section integer,
                -- Target archive package data, set for all published or
                -- pending packages.
                t_sspph integer,
                t_sourcepackagerelease integer,
                t_version text,
                -- Whether a target package became obsolete due to a more
                -- recent source package.
                obsoleted boolean DEFAULT false NOT NULL,
                missing boolean DEFAULT false NOT NULL,
                sourcepackagename text NOT NULL
            );
            CREATE INDEX source_name_index
            ON tmp_merge_copy_data USING btree (sourcepackagename);
        """)
        # Populate the temporary table with package data from the target
        # archive considering the distroseries, pocket and component.
        pop_query = """
            INSERT INTO tmp_merge_copy_data (
                t_sspph, t_sourcepackagerelease, sourcepackagename, t_version)
            SELECT
                secsrc.id AS t_sspph,
                secsrc.sourcepackagerelease AS t_sourcepackagerelease,
                spn.name AS sourcepackagerelease, spr.version AS t_version
            FROM
                securesourcepackagepublishinghistory secsrc,
                sourcepackagerelease spr, sourcepackagename spn
            WHERE
                secsrc.archive = %s AND secsrc.status IN (%s, %s) AND
                secsrc.distroseries = %s AND secsrc.pocket = %s AND
                secsrc.sourcepackagerelease = spr.id AND
                spr.sourcepackagename = spn.id
        """ % sqlvalues(
                destination.archive,
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED,
                destination.distroseries, destination.pocket)
        
        if destination.component is not None:
            pop_query += (
                " AND secsrc.component = %s" % quote(destination.component))
        store.execute(pop_query)

    def _clone_source_packages(self, origin, destination):
        """Copy source publishing data from origin to destination.

        @type origin: PackageLocation
        @param origin: the location from which source publishing
            records are to be copied.
        @type destination: PackageLocation
        @param destination: the location to which the data is
            to be copied.
        """
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        store.execute('''
            INSERT INTO SecureSourcePackagePublishingHistory (
                sourcepackagerelease, distroseries, status, component,
                section, archive, datecreated, datepublished, pocket,
                embargo)
            SELECT spph.sourcepackagerelease, %s as distroseries,
                   spph.status, spph.component, spph.section, %s as archive,
                   %s as datecreated, %s as datepublished,
                   %s as pocket, false as embargo
            FROM SourcePackagePublishingHistory AS spph
            WHERE spph.distroseries = %s AND spph.status in (%s, %s) AND
                  spph.pocket = %s and spph.archive = %s
            ''' % sqlvalues(
                destination.distroseries, destination.archive, UTC_NOW,
                UTC_NOW, destination.pocket, origin.distroseries,
                PackagePublishingStatus.PENDING,
                PackagePublishingStatus.PUBLISHED,
                origin.pocket, origin.archive))

    def packageSetDiff(self, origin, destination, logger=None):
        """Please see `IPackageCloner`."""
        # Find packages that are obsolete or missing in the target archive.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        self._init_packageset_delta(destination)
        self._compute_packageset_delta(origin)

        # Get the list of SecureSourcePackagePublishingHistory keys for
        # source packages that are fresher in the origin archive.
        fresher_packages = store.execute("""
            SELECT s_sspph FROM tmp_merge_copy_data WHERE obsoleted = True;
        """)

        # Get the list of SecureSourcePackagePublishingHistory keys for
        # source packages that are new in the origin archive.
        new_packages = store.execute("""
            SELECT s_sspph FROM tmp_merge_copy_data WHERE missing = True;
        """)

        if logger is not None:
            self._print_diagnostics(logger, store)

        return (
            [package for [package] in fresher_packages],
            [package for [package] in new_packages],
            )

    def _print_diagnostics(self, logger, store):
        """Print details of source packages that are fresher or new.

        Details of packages that are fresher or new in the origin archive
        are logged using the supplied 'logger' instance. This data is only
        available after a package set delta has been computed (see
        packageSetDiff()).
        """
        fresher_info = sorted(store.execute("""
            SELECT sourcepackagename, s_version, t_version
            FROM tmp_merge_copy_data WHERE obsoleted = True;
        """))
        logger.info('Fresher packages: %d' % len(fresher_info))
        for info in fresher_info:
            logger.info('* %s (%s > %s)' % info)
        new_info = sorted(store.execute("""
            SELECT sourcepackagename, s_version
            FROM tmp_merge_copy_data WHERE missing = True;
        """))
        logger.info('New packages: %d' % len(new_info))
        for info in new_info:
            logger.info('* %s (%s)' % info)
 

