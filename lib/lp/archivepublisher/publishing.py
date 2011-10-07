# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'GLOBAL_PUBLISHER_LOCK',
    'Publisher',
    'getPublisher',
    ]

__metaclass__ = type

from datetime import datetime
import errno
import hashlib
import logging
import os
import shutil

from debian.deb822 import (
    Release,
    _multivalued,
    )

from canonical.database.sqlbase import sqlvalues
from canonical.librarian.client import LibrarianClient
from lp.archivepublisher import HARDCODED_COMPONENT_ORDER
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.diskpool import DiskPool
from lp.archivepublisher.domination import Dominator
from lp.archivepublisher.htaccess import (
    htpasswd_credentials_for_archive,
    write_htaccess,
    write_htpasswd,
    )
from lp.archivepublisher.interfaces.archivesigningkey import (
    IArchiveSigningKey,
    )
from lp.archivepublisher.model.ftparchive import FTPArchiveHandler
from lp.archivepublisher.utils import (
    get_ppa_reference,
    RepositoryIndexFile,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.enums import (
    ArchivePurpose,
    ArchiveStatus,
    BinaryPackageFormat,
    PackagePublishingStatus,
    )

# Use this as the lock file name for all scripts that may manipulate
# archives in the filesystem.  In a Launchpad(Cron)Script, set
# lockfilename to this value to make it use the shared lock.
GLOBAL_PUBLISHER_LOCK = 'launchpad-publisher.lock'


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
    log.debug("Making directories as needed.")
    pubconf.setupArchiveDirs()

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

    htaccess_path = os.path.join(pubconf.htaccessroot, ".htaccess")
    htpasswd_path = os.path.join(pubconf.htaccessroot, ".htpasswd")
    # After the initial htaccess/htpasswd files
    # are created generate_ppa_htaccess is responsible for
    # updating the tokens.
    if not os.path.exists(htaccess_path):
        log.debug("Writing htaccess file.")
        write_htaccess(htaccess_path, pubconf.htaccessroot)
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

    _setupHtaccess(archive, pubconf, log)

    if distsroot is not None:
        log.debug("Overriding dists root with %s." % distsroot)
        pubconf.distsroot = distsroot

    log.debug("Preparing publisher.")

    return Publisher(log, pubconf, disk_pool, archive, allowed_suites)


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
        lengths = [len(str(item['size'])) for item in self[key]]
        return max(lengths)


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

        if not os.path.isdir(config.poolroot):
            raise ValueError("Root %s is not a directory or does "
                             "not exist" % config.poolroot)
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

    def A_publish(self, force_publishing):
        """First step in publishing: actual package publishing.

        Asks each DistroSeries to publish itself, which causes
        publishing records to be updated, and files to be placed on disk
        where necessary.
        If self.allowed_suites is set, restrict the publication procedure
        to them.
        """
        self.log.debug("* Step A: Publishing packages")

        for distroseries in self.distro.series:
            for pocket in self.archive.getPockets():
                if (self.allowed_suites and not (distroseries.name, pocket) in
                    self.allowed_suites):
                    self.log.debug(
                        "* Skipping %s/%s" % (distroseries.name, pocket.name))
                    continue

                more_dirt = distroseries.publish(
                    self._diskpool, self.log, self.archive, pocket,
                    is_careful=force_publishing)

                self.dirty_pockets.update(more_dirt)

    def A2_markPocketsWithDeletionsDirty(self):
        """An intermediate step in publishing to detect deleted packages.

        Mark pockets containing deleted packages (status DELETED or
        OBSOLETE), scheduledeletiondate NULL and dateremoved NULL as
        dirty, to ensure that they are processed in death row.
        """
        from lp.soyuz.model.publishing import (
            SourcePackagePublishingHistory, BinaryPackagePublishingHistory)

        self.log.debug("* Step A2: Mark pockets with deletions as dirty")

        # Query part that is common to both queries below.
        base_query = """
            archive = %s AND
            status = %s AND
            scheduleddeletiondate IS NULL AND
            dateremoved is NULL
            """ % sqlvalues(self.archive,
                            PackagePublishingStatus.DELETED)

        # We need to get a set of (distroseries, pocket) tuples that have
        # publications that are waiting to be deleted.  Each tuple is
        # added to the dirty_pockets set.

        # Loop for each pocket in each distroseries:
        for distroseries in self.distro.series:
            for pocket in self.archive.getPockets():
                if self.cannotModifySuite(distroseries, pocket):
                    # We don't want to mark release pockets dirty in a
                    # stable distroseries, no matter what other bugs
                    # that precede here have dirtied it.
                    continue
                clauses = [base_query]
                clauses.append("pocket = %s" % sqlvalues(pocket))
                clauses.append("distroseries = %s" % sqlvalues(distroseries))

                # Make the source publications query.
                source_query = " AND ".join(clauses)
                sources = SourcePackagePublishingHistory.select(source_query)
                if sources.count() > 0:
                    self.markPocketDirty(distroseries, pocket)
                    # No need to check binaries if the pocket is already
                    # dirtied from a source.
                    continue

                # Make the binary publications query.
                clauses = [base_query]
                clauses.append("pocket = %s" % sqlvalues(pocket))
                clauses.append("DistroArchSeries = DistroArchSeries.id")
                clauses.append("DistroArchSeries.distroseries = %s" %
                    sqlvalues(distroseries))
                binary_query = " AND ".join(clauses)
                binaries = BinaryPackagePublishingHistory.select(binary_query,
                    clauseTables=['DistroArchSeries'])
                if binaries.count() > 0:
                    self.markPocketDirty(distroseries, pocket)

    def B_dominate(self, force_domination):
        """Second step in publishing: domination."""
        self.log.debug("* Step B: dominating packages")
        judgejudy = Dominator(self.log, self.archive)
        for distroseries in self.distro.series:
            for pocket in self.archive.getPockets():
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

        source_index_root = os.path.join(
            self._config.distsroot, suite_name, component.name, 'source')
        source_index = RepositoryIndexFile(
            source_index_root, self._config.temproot, 'Sources')

        for spp in distroseries.getSourcePackagePublishing(
            PackagePublishingStatus.PUBLISHED, pocket=pocket,
            component=component, archive=self.archive):
            stanza = spp.getIndexStanza().encode('utf8') + '\n\n'
            source_index.write(stanza)

        source_index.close()

        for arch in distroseries.architectures:
            if not arch.enabled:
                continue

            arch_path = 'binary-%s' % arch.architecturetag

            self.log.debug("Generating Packages for %s" % arch_path)

            package_index_root = os.path.join(
                self._config.distsroot, suite_name, component.name, arch_path)
            package_index = RepositoryIndexFile(
                package_index_root, self._config.temproot, 'Packages')

            di_index_root = os.path.join(
                self._config.distsroot, suite_name, component.name,
                'debian-installer', arch_path)
            di_index = RepositoryIndexFile(
                di_index_root, self._config.temproot, 'Packages')

            for bpp in distroseries.getBinaryPackagePublishing(
                archtag=arch.architecturetag, pocket=pocket,
                component=component, archive=self.archive):
                stanza = bpp.getIndexStanza().encode('utf-8') + '\n\n'
                if (bpp.binarypackagerelease.binpackageformat in
                    (BinaryPackageFormat.DEB, BinaryPackageFormat.DDEB)):
                    package_index.write(stanza)
                elif (bpp.binarypackagerelease.binpackageformat ==
                      BinaryPackageFormat.UDEB):
                    di_index.write(stanza)
                else:
                    self.log.debug(
                        "Cannot publish %s because it is not a DEB or "
                        "UDEB file" % bpp.displayname)

            package_index.close()
            di_index.close()

    def cannotModifySuite(self, distroseries, pocket):
        """Return True if the distroseries is stable and pocket is release."""
        return (not distroseries.isUnstable() and
                not self.archive.allowUpdatesToReleasePocket() and
                pocket == PackagePublishingPocket.RELEASE)

    def checkDirtySuiteBeforePublishing(self, distroseries, pocket):
        """Last check before publishing a dirty suite.

        If the distroseries is stable and the archive doesn't allow updates
        in RELEASE pocket (primary archives) we certainly have a problem,
        better stop.
        """
        if self.cannotModifySuite(distroseries, pocket):
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

        drsummary = "%s %s " % (self.distro.displayname,
                                distroseries.displayname)
        if pocket == PackagePublishingPocket.RELEASE:
            drsummary += distroseries.version
        else:
            drsummary += pocket.name.capitalize()

        suite = distroseries.getSuite(pocket)
        release_file = Release()
        release_file["Origin"] = self._getOrigin()
        release_file["Label"] = self._getLabel()
        release_file["Suite"] = suite
        release_file["Version"] = distroseries.version
        release_file["Codename"] = distroseries.name
        release_file["Date"] = datetime.utcnow().strftime(
            "%a, %d %b %Y %k:%M:%S UTC")
        release_file["Architectures"] = " ".join(
            sorted(list(all_architectures)))
        release_file["Components"] = " ".join(
            reorder_components(all_components))
        release_file["Description"] = drsummary
        if (pocket == PackagePublishingPocket.BACKPORTS and
            distroseries.backports_not_automatic):
            release_file["NotAutomatic"] = "yes"
            release_file["ButAutomaticUpgrades"] = "yes"

        for filename in sorted(list(all_files), key=os.path.dirname):
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

        f = open(os.path.join(
            self._config.distsroot, suite, "Release"), "w")
        try:
            release_file.dump(f, "utf-8")
        finally:
            f.close()

        # Skip signature if the archive signing key is undefined.
        if self.archive.signing_key is None:
            self.log.debug("No signing key available, skipping signature.")
            return

        # Sign the repository.
        archive_signer = IArchiveSigningKey(self.archive)
        archive_signer.signRepository(suite)

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

        f = open(os.path.join(self._config.distsroot, suite,
                              component, arch_path, "Release"), "w")
        try:
            release_file.dump(f, "utf-8")
        finally:
            f.close()

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
        # Only the primary and PPA archives have debian-installer.
        if self.archive.purpose != ArchivePurpose.PARTNER:
            # Set up the debian-installer paths for main_archive.
            # d-i paths are nested inside the component.
            di_path = os.path.join(
                component, "debian-installer", arch_path)
            di_file_stub = os.path.join(di_path, file_stub)
            all_series_files.update(get_suffixed_indices(di_file_stub))
        self._writeSuiteArchOrSource(
            distroseries, pocket, component, 'Packages', arch_name, arch_path,
            all_series_files)

    def _writeSuiteI18n(self, distroseries, pocket, component,
                        all_series_files):
        """Write out an Index file for translation files in a suite."""
        suite = distroseries.getSuite(pocket)
        self.log.debug("Writing Index file for %s/%s/i18n" % (
            suite, component))

        i18n_dir = os.path.join(self._config.distsroot, suite, component,
                                "i18n")
        i18n_files = []
        try:
            for i18n_file in os.listdir(i18n_dir):
                if not i18n_file.startswith('Translation-'):
                    continue
                if not i18n_file.endswith('.bz2'):
                    # Save bandwidth: mirrors should only need the .bz2
                    # versions.
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
                suite, os.path.join(component, "i18n", i18n_file))
            if entry is None:
                continue
            i18n_index.setdefault("SHA1", []).append({
                "sha1": hashlib.sha1(entry).hexdigest(),
                "name": i18n_file,
                "size": len(entry)})

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

        in_file = open(full_name, 'r')
        try:
            return in_file.read()
        finally:
            in_file.close()

    def deleteArchive(self):
        """Delete the archive.

        Physically remove the entire archive from disk and set the archive's
        status to DELETED.

        Any errors encountered while removing the archive from disk will
        be caught and an OOPS report generated.
        """

        root_dir = os.path.join(
            self._config.distroroot, self.archive.owner.name,
            self.archive.name)

        self.log.info(
            "Attempting to delete archive '%s/%s' at '%s'." % (
                self.archive.owner.name, self.archive.name, root_dir))

        for directory in (root_dir, self._config.metaroot):
            if not os.path.exists(directory):
                continue
            try:
                shutil.rmtree(directory)
            except (shutil.Error, OSError), e:
                self.log.warning(
                    "Failed to delete directory '%s' for archive "
                    "'%s/%s'\n%s" % (
                    directory, self.archive.owner.name,
                    self.archive.name, e))

        self.archive.status = ArchiveStatus.DELETED
        self.archive.publish = False
