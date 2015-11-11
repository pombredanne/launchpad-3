# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'cannot_modify_suite',
    'FORMAT_TO_SUBCOMPONENT',
    'GLOBAL_PUBLISHER_LOCK',
    'Publisher',
    'getPublisher',
    ]

__metaclass__ = type

from datetime import datetime
import errno
import hashlib
from itertools import (
    chain,
    groupby,
    )
import logging
from operator import attrgetter
import os
import shutil

from debian.deb822 import (
    _multivalued,
    Release,
    )
from storm.expr import Desc
from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archivepublisher import HARDCODED_COMPONENT_ORDER
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.diskpool import DiskPool
from lp.archivepublisher.domination import Dominator
from lp.archivepublisher.htaccess import (
    htpasswd_credentials_for_archive,
    write_htaccess,
    write_htpasswd,
    )
from lp.archivepublisher.indices import (
    build_binary_stanza_fields,
    build_source_stanza_fields,
    build_translations_stanza_fields,
    )
from lp.archivepublisher.interfaces.archivesigningkey import (
    IArchiveSigningKey,
    )
from lp.archivepublisher.model.ftparchive import FTPArchiveHandler
from lp.archivepublisher.utils import (
    get_ppa_reference,
    RepositoryIndexFile,
    )
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.model.distroseries import DistroSeries
from lp.services.database.constants import UTC_NOW
from lp.services.database.interfaces import IStore
from lp.services.features import getFeatureFlag
from lp.services.librarian.client import LibrarianClient
from lp.services.utils import file_exists
from lp.soyuz.enums import (
    ArchivePurpose,
    ArchiveStatus,
    BinaryPackageFormat,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.archive import NoSuchPPA
from lp.soyuz.interfaces.publishing import (
    active_publishing_status,
    IPublishingSet,
    )
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.model.publishing import (
    BinaryPackagePublishingHistory,
    SourcePackagePublishingHistory,
    )

# Use this as the lock file name for all scripts that may manipulate
# archives in the filesystem.  In a Launchpad(Cron)Script, set
# lockfilename to this value to make it use the shared lock.
GLOBAL_PUBLISHER_LOCK = 'launchpad-publisher.lock'


FORMAT_TO_SUBCOMPONENT = {
    BinaryPackageFormat.UDEB: 'debian-installer',
    BinaryPackageFormat.DDEB: 'debug',
    }


def reorder_components(components):
    """Return a list of the components provided.

    The list will be ordered by the semi arbitrary rules of ubuntu.
    Over time this method needs to be removed and replaced by having
    component ordering codified in the database.
    """
    remaining = list(components)
    ordered = []
    for comp in HARDCODED_COMPONENT_ORDER:
        if comp in remaining:
            ordered.append(comp)
            remaining.remove(comp)
    ordered.extend(remaining)
    return ordered


def get_suffixed_indices(path):
    """Return a set of paths to compressed copies of the given index."""
    return set([path + suffix for suffix in ('', '.gz', '.bz2')])


def _getDiskPool(pubconf, log):
    """Return a DiskPool instance for a given PubConf.

    It ensures the given archive location matches the minimal structure
    required.
    """
    log.debug("Preparing on-disk pool representation.")
    dp = DiskPool(pubconf.poolroot, pubconf.temproot,
                  logging.getLogger("DiskPool"))
    # Set the diskpool's log level to INFO to suppress debug output
    dp.logger.setLevel(logging.INFO)

    return dp


def _setupHtaccess(archive, pubconf, log):
    """Setup .htaccess/.htpasswd files for an archive.
    """
    if not archive.private:
        # FIXME: JRV 20101108 leftover .htaccess and .htpasswd files
        # should be removed when support for making existing 3PA's public
        # is added; bug=376072
        return

    htaccess_path = os.path.join(pubconf.archiveroot, ".htaccess")
    htpasswd_path = os.path.join(pubconf.archiveroot, ".htpasswd")
    # After the initial htaccess/htpasswd files
    # are created generate_ppa_htaccess is responsible for
    # updating the tokens.
    if not os.path.exists(htaccess_path):
        log.debug("Writing htaccess file.")
        write_htaccess(htaccess_path, pubconf.archiveroot)
        passwords = htpasswd_credentials_for_archive(archive)
        write_htpasswd(htpasswd_path, passwords)


def getPublisher(archive, allowed_suites, log, distsroot=None):
    """Return an initialized Publisher instance for the given context.

    The callsites can override the location where the archive indexes will
    be stored via 'distroot' argument.
    """
    if archive.purpose != ArchivePurpose.PPA:
        log.debug("Finding configuration for %s %s."
                  % (archive.distribution.name, archive.displayname))
    else:
        log.debug("Finding configuration for '%s' PPA."
                  % archive.owner.name)
    pubconf = getPubConfig(archive)

    disk_pool = _getDiskPool(pubconf, log)

    if distsroot is not None:
        log.debug("Overriding dists root with %s." % distsroot)
        pubconf.distsroot = distsroot

    log.debug("Preparing publisher.")

    return Publisher(log, pubconf, disk_pool, archive, allowed_suites)


def get_sources_path(config, suite_name, component):
    """Return path to Sources file for the given arguments."""
    return os.path.join(
        config.distsroot, suite_name, component.name, "source", "Sources")


def get_packages_path(config, suite_name, component, arch, subcomp=None):
    """Return path to Packages file for the given arguments."""
    component_root = os.path.join(config.distsroot, suite_name, component.name)
    arch_path = "binary-%s" % arch.architecturetag
    if subcomp is None:
        return os.path.join(component_root, arch_path, "Packages")
    else:
        return os.path.join(component_root, subcomp, arch_path, "Packages")


def cannot_modify_suite(archive, distroseries, pocket):
    """Return True for Release pockets of stable series in primary archives."""
    return (not distroseries.isUnstable() and
            not archive.allowUpdatesToReleasePocket() and
            pocket == PackagePublishingPocket.RELEASE)


class I18nIndex(_multivalued):
    """Represents an i18n/Index file."""
    _multivalued_fields = {
        "sha1": ["sha1", "size", "name"],
    }

    @property
    def _fixed_field_lengths(self):
        fixed_field_lengths = {}
        for key in self._multivalued_fields:
            length = self._get_size_field_length(key)
            fixed_field_lengths[key] = {"size": length}
        return fixed_field_lengths

    def _get_size_field_length(self, key):
        return max(len(str(item['size'])) for item in self[key])


class Publisher(object):
    """Publisher is the class used to provide the facility to publish
    files in the pool of a Distribution. The publisher objects will be
    instantiated by the archive build scripts and will be used throughout
    the processing of each DistroSeries and DistroArchSeries in question
    """

    def __init__(self, log, config, diskpool, archive, allowed_suites=None,
                 library=None):
        """Initialize a publisher.

        Publishers need the pool root dir and a DiskPool object.

        Optionally we can pass a list of tuples, (distroseries.name, pocket),
        which will restrict the publisher actions, only suites listed in
        allowed_suites will be modified.
        """
        self.log = log
        self._config = config
        self.distro = archive.distribution
        self.archive = archive
        self.allowed_suites = allowed_suites

        self._diskpool = diskpool

        if library is None:
            self._library = LibrarianClient()
        else:
            self._library = library

        # Track which distroseries pockets have been dirtied by a
        # change, and therefore need domination/apt-ftparchive work.
        # This is a set of tuples in the form (distroseries.name, pocket)
        self.dirty_pockets = set()

        # Track which pockets need release files. This will contain more
        # than dirty_pockets in the case of a careful index run.
        # This is a set of tuples in the form (distroseries.name, pocket)
        self.release_files_needed = set()

    def setupArchiveDirs(self):
        self.log.debug("Setting up archive directories.")
        self._config.setupArchiveDirs()
        _setupHtaccess(self.archive, self._config, self.log)

    def isDirty(self, distroseries, pocket):
        """True if a publication has happened in this release and pocket."""
        return (distroseries.name, pocket) in self.dirty_pockets

    def markPocketDirty(self, distroseries, pocket):
        """Mark a pocket dirty only if it's allowed."""
        if self.isAllowed(distroseries, pocket):
            self.dirty_pockets.add((distroseries.name, pocket))

    def isAllowed(self, distroseries, pocket):
        """Whether or not the given suite should be considered.

        Return True either if the self.allowed_suite is empty (was not
        specified in command line) or if the given suite is included in it.

        Otherwise, return False.
        """
        return (not self.allowed_suites or
                (distroseries.name, pocket) in self.allowed_suites)

    @property
    def subcomponents(self):
        subcomps = []
        if self.archive.purpose != ArchivePurpose.PARTNER:
            subcomps.append('debian-installer')
        if self.archive.publish_debug_symbols:
            subcomps.append('debug')
        return subcomps

    @property
    def consider_series(self):
        if self.archive.purpose in (
            ArchivePurpose.PRIMARY,
            ArchivePurpose.PARTNER,
            ):
            # For PRIMARY and PARTNER archives, skip OBSOLETE and FUTURE
            # series.  We will never want to publish anything in them, so it
            # isn't worth thinking about whether they have pending
            # publications.
            return [
                series
                for series in self.distro.series
                if series.status not in (
                    SeriesStatus.OBSOLETE,
                    SeriesStatus.FUTURE,
                    )]
        else:
            # Other archives may have reasons to continue building at least
            # for OBSOLETE series.  For example, a PPA may be continuing to
            # provide custom builds for users who haven't upgraded yet.
            return self.distro.series

    def checkLegalPocket(self, distroseries, pocket, is_careful):
        """Check if the publication can happen in the archive."""
        if distroseries not in self.consider_series:
            return False
        # 'careful' mode re-publishes everything:
        if is_careful:
            return True
        return self.archive.canModifySuite(distroseries, pocket)

    def getPendingSourcePublications(self, is_careful):
        """Return the specific group of source records to be published."""
        # Careful publishing should include all PUBLISHED rows, normal run
        # only includes PENDING ones.
        statuses = [PackagePublishingStatus.PENDING]
        if is_careful:
            statuses.append(PackagePublishingStatus.PUBLISHED)

        publications = IStore(SourcePackagePublishingHistory).find(
            SourcePackagePublishingHistory,
            SourcePackagePublishingHistory.archive == self.archive,
            SourcePackagePublishingHistory.status.is_in(statuses))
        return publications.order_by(
            SourcePackagePublishingHistory.distroseriesID,
            SourcePackagePublishingHistory.pocket,
            Desc(SourcePackagePublishingHistory.id))

    def publishSources(self, distroseries, pocket, spphs):
        """Publish sources for a given distroseries and pocket."""
        self.log.debug(
            "* Publishing pending sources for %s" %
            distroseries.getSuite(pocket))
        for spph in spphs:
            spph.publish(self._diskpool, self.log)

    def findAndPublishSources(self, is_careful=False):
        """Search for and publish all pending sources.

        :param is_careful: If True, republish all published records (system
            will DTRT checking the hash of all published files).

        Consider records returned by getPendingSourcePublications.
        """
        dirty_pockets = set()
        all_spphs = self.getPendingSourcePublications(is_careful)
        for (distroseries, pocket), spphs in groupby(
                all_spphs, attrgetter("distroseries", "pocket")):
            if not self.isAllowed(distroseries, pocket):
                self.log.debug("* Skipping %s", distroseries.getSuite(pocket))
            elif not self.checkLegalPocket(distroseries, pocket, is_careful):
                for spph in spphs:
                    self.log.error(
                        "Tried to publish %s (%s) into %s (%s), skipping" % (
                            spph.displayname, spph.id,
                            distroseries.getSuite(pocket),
                            distroseries.status.name))
            else:
                self.publishSources(distroseries, pocket, spphs)
                dirty_pockets.add((distroseries.name, pocket))
        return dirty_pockets

    def getPendingBinaryPublications(self, is_careful):
        """Return the specific group of binary records to be published."""
        statuses = [PackagePublishingStatus.PENDING]
        if is_careful:
            statuses.append(PackagePublishingStatus.PUBLISHED)

        publications = IStore(BinaryPackagePublishingHistory).find(
            BinaryPackagePublishingHistory,
            BinaryPackagePublishingHistory.archive == self.archive,
            BinaryPackagePublishingHistory.distroarchseriesID ==
                DistroArchSeries.id,
            DistroArchSeries.distroseriesID == DistroSeries.id,
            BinaryPackagePublishingHistory.status.is_in(statuses))
        return publications.order_by(
            DistroSeries.id,
            BinaryPackagePublishingHistory.pocket,
            DistroArchSeries.architecturetag,
            Desc(BinaryPackagePublishingHistory.id))

    def publishBinaries(self, distroarchseries, pocket, bpphs):
        """Publish binaries for a given distroarchseries and pocket."""
        self.log.debug(
            "* Publishing pending binaries for %s/%s" % (
                distroarchseries.distroseries.getSuite(pocket),
                distroarchseries.architecturetag))
        for bpph in bpphs:
            bpph.publish(self._diskpool, self.log)

    def findAndPublishBinaries(self, is_careful=False):
        """Search for and publish all pending binaries.

        :param is_careful: If True, republish all published records (system
            will DTRT checking the hash of all published files).

        Consider records returned by getPendingBinaryPublications.
        """
        dirty_pockets = set()
        all_bpphs = self.getPendingBinaryPublications(is_careful)
        for (distroarchseries, pocket), bpphs in groupby(
                all_bpphs, attrgetter("distroarchseries", "pocket")):
            distroseries = distroarchseries.distroseries
            if not self.isAllowed(distroseries, pocket):
                pass  # Already logged by publishSources.
            elif not self.checkLegalPocket(distroseries, pocket, is_careful):
                for bpph in bpphs:
                    self.log.error(
                        "Tried to publish %s (%s) into %s (%s), skipping" % (
                            bpph.displayname, bpph.id,
                            distroseries.getSuite(pocket),
                            distroseries.status.name))
            else:
                self.publishBinaries(distroarchseries, pocket, bpphs)
                dirty_pockets.add((distroseries.name, pocket))
        return dirty_pockets

    def A_publish(self, force_publishing):
        """First step in publishing: actual package publishing.

        Publish each DistroSeries, which causes publishing records to be
        updated, and files to be placed on disk where necessary.
        If self.allowed_suites is set, restrict the publication procedure
        to them.
        """
        self.log.debug("* Step A: Publishing packages")

        self.dirty_pockets.update(
            self.findAndPublishSources(is_careful=force_publishing))
        self.dirty_pockets.update(
            self.findAndPublishBinaries(is_careful=force_publishing))

    def A2_markPocketsWithDeletionsDirty(self):
        """An intermediate step in publishing to detect deleted packages.

        Mark pockets containing deleted packages (status DELETED or
        OBSOLETE), scheduledeletiondate NULL and dateremoved NULL as
        dirty, to ensure that they are processed in death row.
        """
        self.log.debug("* Step A2: Mark pockets with deletions as dirty")

        # Query part that is common to both queries below.
        def base_conditions(table):
            return [
                table.archive == self.archive,
                table.status == PackagePublishingStatus.DELETED,
                table.scheduleddeletiondate == None,
                table.dateremoved == None,
                ]

        # We need to get a set of (distroseries, pocket) tuples that have
        # publications that are waiting to be deleted.  Each tuple is
        # added to the dirty_pockets set.

        # Make the source publications query.
        conditions = base_conditions(SourcePackagePublishingHistory)
        conditions.append(
            SourcePackagePublishingHistory.distroseriesID == DistroSeries.id)
        source_suites = IStore(SourcePackagePublishingHistory).find(
            (DistroSeries, SourcePackagePublishingHistory.pocket),
            *conditions).config(distinct=True).order_by(
                DistroSeries.id, SourcePackagePublishingHistory.pocket)

        # Make the binary publications query.
        conditions = base_conditions(BinaryPackagePublishingHistory)
        conditions.extend([
            BinaryPackagePublishingHistory.distroarchseriesID ==
                DistroArchSeries.id,
            DistroArchSeries.distroseriesID == DistroSeries.id,
            ])
        binary_suites = IStore(BinaryPackagePublishingHistory).find(
            (DistroSeries, BinaryPackagePublishingHistory.pocket),
            *conditions).config(distinct=True).order_by(
                DistroSeries.id, BinaryPackagePublishingHistory.pocket)

        for distroseries, pocket in chain(source_suites, binary_suites):
            if self.isDirty(distroseries, pocket):
                continue
            if (cannot_modify_suite(self.archive, distroseries, pocket)
                or not self.isAllowed(distroseries, pocket)):
                # We don't want to mark release pockets dirty in a
                # stable distroseries, no matter what other bugs
                # that precede here have dirtied it.
                continue
            self.markPocketDirty(distroseries, pocket)

    def B_dominate(self, force_domination):
        """Second step in publishing: domination."""
        self.log.debug("* Step B: dominating packages")
        judgejudy = Dominator(self.log, self.archive)
        for distroseries in self.distro.series:
            for pocket in self.archive.getPockets():
                if not self.isAllowed(distroseries, pocket):
                    continue
                if not force_domination:
                    if not self.isDirty(distroseries, pocket):
                        self.log.debug("Skipping domination for %s/%s" %
                                   (distroseries.name, pocket.name))
                        continue
                    self.checkDirtySuiteBeforePublishing(distroseries, pocket)
                judgejudy.judgeAndDominate(distroseries, pocket)

    def C_doFTPArchive(self, is_careful):
        """Does the ftp-archive step: generates Sources and Packages."""
        self.log.debug("* Step C: Set apt-ftparchive up and run it")
        apt_handler = FTPArchiveHandler(self.log, self._config,
                                        self._diskpool, self.distro,
                                        self)
        apt_handler.run(is_careful)

    def C_writeIndexes(self, is_careful):
        """Write Index files (Packages & Sources) using LP information.

        Iterates over all distroseries and its pockets and components.
        """
        self.log.debug("* Step C': write indexes directly from DB")
        for distroseries in self.distro:
            for pocket in self.archive.getPockets():
                if not is_careful:
                    if not self.isDirty(distroseries, pocket):
                        self.log.debug("Skipping index generation for %s/%s" %
                                       (distroseries.name, pocket.name))
                        continue
                    self.checkDirtySuiteBeforePublishing(distroseries, pocket)

                self.release_files_needed.add((distroseries.name, pocket))

                components = self.archive.getComponentsForSeries(distroseries)
                for component in components:
                    self._writeComponentIndexes(
                        distroseries, pocket, component)

    def D_writeReleaseFiles(self, is_careful):
        """Write out the Release files for the provided distribution.

        If is_careful is specified, we include all pockets of all releases.

        Otherwise we include only pockets flagged as true in dirty_pockets.
        """
        self.log.debug("* Step D: Generating Release files.")
        for distroseries in self.distro:
            for pocket in self.archive.getPockets():
                if not is_careful:
                    if not self.isDirty(distroseries, pocket):
                        self.log.debug("Skipping release files for %s/%s" %
                                       (distroseries.name, pocket.name))
                        continue
                    self.checkDirtySuiteBeforePublishing(distroseries, pocket)
                self._writeSuite(distroseries, pocket)

    def _allIndexFiles(self, distroseries):
        """Return all index files on disk for a distroseries."""
        components = self.archive.getComponentsForSeries(distroseries)
        for pocket in self.archive.getPockets():
            suite_name = distroseries.getSuite(pocket)
            for component in components:
                yield get_sources_path(self._config, suite_name, component)
                for arch in distroseries.architectures:
                    if not arch.enabled:
                        continue
                    yield get_packages_path(
                        self._config, suite_name, component, arch)
                    for subcomp in self.subcomponents:
                        yield get_packages_path(
                            self._config, suite_name, component, arch, subcomp)

    def _latestNonEmptySeries(self):
        """Find the latest non-empty series in an archive.

        Doing this properly (series with highest version and any active
        publications) is expensive.  However, we just went to the effort of
        publishing everything; so a quick-and-dirty approach is to look
        through what we published on disk.
        """
        for distroseries in self.distro:
            for index in self._allIndexFiles(distroseries):
                try:
                    if os.path.getsize(index) > 0:
                        return distroseries
                except OSError:
                    pass

    def createSeriesAliases(self):
        """Ensure that any series aliases exist.

        The natural implementation would be to point the alias at
        self.distro.currentseries, but that works poorly for PPAs, where
        it's possible that no packages have been published for the current
        series.  We also don't want to have to go through and republish all
        PPAs when we create a new series.  Thus, we instead do the best we
        can by pointing the alias at the latest series with any publications
        in the archive, which is the best approximation to a development
        series for that PPA.

        This does mean that the published alias might point to an older
        series, then you upload something to the alias and find that the
        alias has now moved to a newer series.  What can I say?  The
        requirements are not entirely coherent for PPAs given that packages
        are not automatically copied forward.
        """
        alias = self.distro.development_series_alias
        if alias is not None:
            current = self._latestNonEmptySeries()
            if current is None:
                return
            for pocket in self.archive.getPockets():
                alias_suite = "%s%s" % (alias, pocketsuffix[pocket])
                current_suite = current.getSuite(pocket)
                current_suite_path = os.path.join(
                    self._config.distsroot, current_suite)
                if not os.path.isdir(current_suite_path):
                    continue
                alias_suite_path = os.path.join(
                    self._config.distsroot, alias_suite)
                if os.path.islink(alias_suite_path):
                    if os.readlink(alias_suite_path) == current_suite:
                        continue
                elif os.path.isdir(alias_suite_path):
                    # Perhaps somebody did something misguided ...
                    self.log.warning(
                        "Alias suite path %s is a directory!" % alias_suite)
                    continue
                try:
                    os.unlink(alias_suite_path)
                except OSError:
                    pass
                os.symlink(current_suite, alias_suite_path)

    def _writeComponentIndexes(self, distroseries, pocket, component):
        """Write Index files for single distroseries + pocket + component.

        Iterates over all supported architectures and 'sources', no
        support for installer-* yet.
        Write contents using LP info to an extra plain file (Packages.lp
        and Sources.lp .
        """
        suite_name = distroseries.getSuite(pocket)
        self.log.debug("Generate Indexes for %s/%s"
                       % (suite_name, component.name))

        self.log.debug("Generating Sources")

        separate_long_descriptions = False
        if (not distroseries.include_long_descriptions and
                getFeatureFlag("soyuz.ppa.separate_long_descriptions")):
            # If include_long_descriptions is False and the feature flag is
            # enabled, create a Translation-en file.
            # build_binary_stanza_fields will also omit long descriptions
            # from the Packages.
            separate_long_descriptions = True
            packages = set()
            translation_en = RepositoryIndexFile(
                os.path.join(self._config.distsroot, suite_name,
                             component.name, "i18n", "Translation-en"),
                self._config.temproot)

        source_index = RepositoryIndexFile(
            get_sources_path(self._config, suite_name, component),
            self._config.temproot)

        for spp in distroseries.getSourcePackagePublishing(
                pocket, component, self.archive):
            stanza = build_source_stanza_fields(
                spp.sourcepackagerelease, spp.component, spp.section)
            source_index.write(stanza.makeOutput().encode('utf-8') + '\n\n')

        source_index.close()

        for arch in distroseries.architectures:
            if not arch.enabled:
                continue

            arch_path = 'binary-%s' % arch.architecturetag

            self.log.debug("Generating Packages for %s" % arch_path)

            indices = {}
            indices[None] = RepositoryIndexFile(
                get_packages_path(self._config, suite_name, component, arch),
                self._config.temproot)

            for subcomp in self.subcomponents:
                indices[subcomp] = RepositoryIndexFile(
                    get_packages_path(
                        self._config, suite_name, component, arch, subcomp),
                    self._config.temproot)

            for bpp in distroseries.getBinaryPackagePublishing(
                    arch.architecturetag, pocket, component, self.archive):
                subcomp = FORMAT_TO_SUBCOMPONENT.get(
                    bpp.binarypackagerelease.binpackageformat)
                if subcomp not in indices:
                    # Skip anything that we're not generating indices
                    # for, eg. ddebs where publish_debug_symbols is
                    # disabled.
                    continue
                stanza = build_binary_stanza_fields(
                    bpp.binarypackagerelease, bpp.component, bpp.section,
                    bpp.priority, bpp.phased_update_percentage,
                    separate_long_descriptions)
                indices[subcomp].write(
                    stanza.makeOutput().encode('utf-8') + '\n\n')
                if separate_long_descriptions:
                    # If the (Package, Description-md5) pair already exists
                    # in the set, build_translations_stanza_fields will
                    # return None. Otherwise it will add the pair to
                    # the set and return a stanza to be written to
                    # Translation-en.
                    translation_stanza = build_translations_stanza_fields(
                        bpp.binarypackagerelease, packages)
                    if translation_stanza is not None:
                        translation_en.write(
                            translation_stanza.makeOutput().encode('utf-8')
                            + '\n\n')

            for index in indices.itervalues():
                index.close()

        if separate_long_descriptions:
            translation_en.close()

    def checkDirtySuiteBeforePublishing(self, distroseries, pocket):
        """Last check before publishing a dirty suite.

        If the distroseries is stable and the archive doesn't allow updates
        in RELEASE pocket (primary archives) we certainly have a problem,
        better stop.
        """
        if cannot_modify_suite(self.archive, distroseries, pocket):
            raise AssertionError(
                "Oops, tainting RELEASE pocket of %s." % distroseries)

    def _getLabel(self):
        """Return the contents of the Release file Label field.

        :return: a text that should be used as the value of the Release file
            'Label' field.
        """
        if self.archive.is_ppa:
            return self.archive.displayname
        elif self.archive.purpose == ArchivePurpose.PARTNER:
            return "Partner archive"
        else:
            return self.distro.displayname

    def _getOrigin(self):
        """Return the contents of the Release file Origin field.

        Primary, Partner and Copy archives use the distribution displayname.
        For PPAs we use a more specific value that follows
        `get_ppa_reference`.

        :return: a text that should be used as the value of the Release file
            'Origin' field.
        """
        # XXX al-maisan, 2008-11-19, bug=299981. If this file is released
        # from a copy archive then modify the origin to indicate so.
        if self.archive.purpose == ArchivePurpose.PARTNER:
            return "Canonical"
        if not self.archive.is_ppa:
            return self.distro.displayname
        return "LP-PPA-%s" % get_ppa_reference(self.archive)

    def _writeReleaseFile(self, suite, release_data):
        """Write a Release file to the archive.

        :param suite: The name of the suite whose Release file is to be
            written.
        :param release_data: A `debian.deb822.Release` object to write
            to the filesystem.
        """
        location = os.path.join(self._config.distsroot, suite)
        if not file_exists(location):
            os.makedirs(location)
        with open(os.path.join(location, "Release"), "w") as release_file:
            release_data.dump(release_file, "utf-8")

    def _syncTimestamps(self, suite, all_files):
        """Make sure the timestamps on all files in a suite match."""
        location = os.path.join(self._config.distsroot, suite)
        paths = [os.path.join(location, path) for path in all_files]
        latest_timestamp = max(os.stat(path).st_mtime for path in paths)
        for path in paths:
            os.utime(path, (latest_timestamp, latest_timestamp))

    def _writeSuite(self, distroseries, pocket):
        """Write out the Release files for the provided suite."""
        # XXX: kiko 2006-08-24: Untested method.

        # As we generate file lists for apt-ftparchive we record which
        # distroseriess and so on we need to generate Release files for.
        # We store this in release_files_needed and consume the information
        # when writeReleaseFiles is called.
        if (distroseries.name, pocket) not in self.release_files_needed:
            # If we don't need to generate a release for this release
            # and pocket, don't!
            return

        suite = distroseries.getSuite(pocket)
        all_components = [
            comp.name for comp in
            self.archive.getComponentsForSeries(distroseries)]
        all_architectures = [
            a.architecturetag for a in distroseries.enabled_architectures]
        all_files = set()
        for component in all_components:
            self._writeSuiteSource(
                distroseries, pocket, component, all_files)
            for architecture in all_architectures:
                self._writeSuiteArch(
                    distroseries, pocket, component, architecture, all_files)
            self._writeSuiteI18n(
                distroseries, pocket, component, all_files)
        for architecture in all_architectures:
            for contents_path in get_suffixed_indices(
                    'Contents-' + architecture):
                if os.path.exists(os.path.join(
                        self._config.distsroot, suite, contents_path)):
                    all_files.add(contents_path)

        drsummary = "%s %s " % (self.distro.displayname,
                                distroseries.displayname)
        if pocket == PackagePublishingPocket.RELEASE:
            drsummary += distroseries.version
        else:
            drsummary += pocket.name.capitalize()

        release_file = Release()
        release_file["Origin"] = self._getOrigin()
        release_file["Label"] = self._getLabel()
        release_file["Suite"] = suite
        release_file["Version"] = distroseries.version
        release_file["Codename"] = distroseries.name
        release_file["Date"] = datetime.utcnow().strftime(
            "%a, %d %b %Y %k:%M:%S UTC")
        release_file["Architectures"] = " ".join(sorted(all_architectures))
        release_file["Components"] = " ".join(
            reorder_components(all_components))
        release_file["Description"] = drsummary
        if (pocket == PackagePublishingPocket.BACKPORTS and
            distroseries.backports_not_automatic):
            release_file["NotAutomatic"] = "yes"
            release_file["ButAutomaticUpgrades"] = "yes"

        for filename in sorted(all_files, key=os.path.dirname):
            entry = self._readIndexFileContents(suite, filename)
            if entry is None:
                continue
            release_file.setdefault("MD5Sum", []).append({
                "md5sum": hashlib.md5(entry).hexdigest(),
                "name": filename,
                "size": len(entry)})
            release_file.setdefault("SHA1", []).append({
                "sha1": hashlib.sha1(entry).hexdigest(),
                "name": filename,
                "size": len(entry)})
            release_file.setdefault("SHA256", []).append({
                "sha256": hashlib.sha256(entry).hexdigest(),
                "name": filename,
                "size": len(entry)})

        self._writeReleaseFile(suite, release_file)
        all_files.add("Release")

        if self.archive.signing_key is not None:
            # Sign the repository.
            IArchiveSigningKey(self.archive).signRepository(suite)
            all_files.add("Release.gpg")
            all_files.add("InRelease")
        else:
            # Skip signature if the archive signing key is undefined.
            self.log.debug("No signing key available, skipping signature.")

        # Make sure all the timestamps match, to make it easier to insert
        # caching headers on mirrors.
        self._syncTimestamps(suite, all_files)

    def _writeSuiteArchOrSource(self, distroseries, pocket, component,
                                file_stub, arch_name, arch_path,
                                all_series_files):
        """Write out a Release file for an architecture or source."""
        # XXX kiko 2006-08-24: Untested method.

        suite = distroseries.getSuite(pocket)
        self.log.debug("Writing Release file for %s/%s/%s" % (
            suite, component, arch_path))

        # Now, grab the actual (non-di) files inside each of
        # the suite's architectures
        file_stub = os.path.join(component, arch_path, file_stub)

        all_series_files.update(get_suffixed_indices(file_stub))
        all_series_files.add(os.path.join(component, arch_path, "Release"))

        release_file = Release()
        release_file["Archive"] = suite
        release_file["Version"] = distroseries.version
        release_file["Component"] = component
        release_file["Origin"] = self._getOrigin()
        release_file["Label"] = self._getLabel()
        release_file["Architecture"] = arch_name

        with open(os.path.join(self._config.distsroot, suite,
                               component, arch_path, "Release"), "w") as f:
            release_file.dump(f, "utf-8")

    def _writeSuiteSource(self, distroseries, pocket, component,
                          all_series_files):
        """Write out a Release file for a suite's sources."""
        self._writeSuiteArchOrSource(
            distroseries, pocket, component, 'Sources', 'source', 'source',
            all_series_files)

    def _writeSuiteArch(self, distroseries, pocket, component,
                        arch_name, all_series_files):
        """Write out a Release file for an architecture in a suite."""
        file_stub = 'Packages'
        arch_path = 'binary-' + arch_name

        for subcomp in self.subcomponents:
            # Set up the subcomponent paths.
            sub_path = os.path.join(component, subcomp, arch_path)
            sub_file_stub = os.path.join(sub_path, file_stub)
            all_series_files.update(get_suffixed_indices(sub_file_stub))
        self._writeSuiteArchOrSource(
            distroseries, pocket, component, 'Packages', arch_name, arch_path,
            all_series_files)

    def _writeSuiteI18n(self, distroseries, pocket, component,
                        all_series_files):
        """Write out an Index file for translation files in a suite."""
        suite = distroseries.getSuite(pocket)
        self.log.debug("Writing Index file for %s/%s/i18n" % (
            suite, component))

        i18n_subpath = os.path.join(component, "i18n")
        i18n_dir = os.path.join(self._config.distsroot, suite, i18n_subpath)
        i18n_files = []
        try:
            for i18n_file in os.listdir(i18n_dir):
                if not i18n_file.startswith('Translation-'):
                    continue
                i18n_files.append(i18n_file)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
        if not i18n_files:
            # If the i18n directory doesn't exist or is empty, we don't need
            # to index it.
            return

        i18n_index = I18nIndex()
        for i18n_file in sorted(i18n_files):
            entry = self._readIndexFileContents(
                suite, os.path.join(i18n_subpath, i18n_file))
            if entry is None:
                continue
            i18n_index.setdefault("SHA1", []).append({
                "sha1": hashlib.sha1(entry).hexdigest(),
                "name": i18n_file,
                "size": len(entry)})
            # Schedule i18n files for inclusion in the Release file.
            all_series_files.add(os.path.join(i18n_subpath, i18n_file))

        with open(os.path.join(i18n_dir, "Index"), "w") as f:
            i18n_index.dump(f, "utf-8")

        # Schedule this for inclusion in the Release file.
        all_series_files.add(os.path.join(component, "i18n", "Index"))

    def _readIndexFileContents(self, distroseries_name, file_name):
        """Read an index files' contents.

        :param distroseries_name: Distro series name
        :param file_name: Filename relative to the parent container directory.
        :return: File contents, or None if the file could not be found.
        """
        full_name = os.path.join(self._config.distsroot,
                                 distroseries_name, file_name)
        if not os.path.exists(full_name):
            # The file we were asked to write out doesn't exist.
            # Most likely we have an incomplete archive (E.g. no sources
            # for a given distroseries). This is a non-fatal issue
            self.log.debug("Failed to find " + full_name)
            return None

        with open(full_name, 'r') as in_file:
            return in_file.read()

    def deleteArchive(self):
        """Delete the archive.

        Physically remove the entire archive from disk and set the archive's
        status to DELETED.

        Any errors encountered while removing the archive from disk will
        be caught and an OOPS report generated.
        """
        assert self.archive.is_ppa
        self.log.info(
            "Attempting to delete archive '%s/%s' at '%s'." % (
                self.archive.owner.name, self.archive.name,
                self._config.archiveroot))

        # Set all the publications to DELETED.
        sources = self.archive.getPublishedSources(
            status=active_publishing_status)
        getUtility(IPublishingSet).requestDeletion(
            sources, removed_by=getUtility(ILaunchpadCelebrities).janitor,
            removal_comment="Removed when deleting archive")

        # Deleting the sources will have killed the corresponding
        # binaries too, but there may be orphaned leftovers (eg. NBS).
        binaries = self.archive.getAllPublishedBinaries(
            status=active_publishing_status)
        getUtility(IPublishingSet).requestDeletion(
            binaries, removed_by=getUtility(ILaunchpadCelebrities).janitor,
            removal_comment="Removed when deleting archive")

        # Now set dateremoved on any publication that doesn't already
        # have it set, so things can expire from the librarian.
        for pub in self.archive.getPublishedSources(include_removed=False):
            pub.dateremoved = UTC_NOW
        for pub in self.archive.getAllPublishedBinaries(include_removed=False):
            pub.dateremoved = UTC_NOW

        for directory in (self._config.archiveroot, self._config.metaroot):
            if directory is None or not os.path.exists(directory):
                continue
            try:
                shutil.rmtree(directory)
            except (shutil.Error, OSError) as e:
                self.log.warning(
                    "Failed to delete directory '%s' for archive "
                    "'%s/%s'\n%s" % (
                    directory, self.archive.owner.name,
                    self.archive.name, e))

        self.archive.status = ArchiveStatus.DELETED
        self.archive.publish = False

        # Now that it's gone from disk we can rename the archive to free
        # up the namespace.
        new_name = base_name = '%s-deletedppa' % self.archive.name
        count = 1
        while True:
            try:
                self.archive.owner.getPPAByName(
                    self.archive.distribution, new_name)
            except NoSuchPPA:
                break
            new_name = '%s%d' % (base_name, count)
            count += 1
        self.archive.name = new_name
        self.log.info("Renamed deleted archive '%s'.", self.archive.reference)
