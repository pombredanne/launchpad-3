# (C) Canonical Software Ltd. 2004-2006, all rights reserved.

__all__ = ['Publisher', 'pocketsuffix', 'suffixpocket', 'getPublisher']

__metaclass__ = type

import apt_pkg
from datetime import datetime
import logging
from md5 import md5
import os
from sha import sha

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.archivepublisher import HARDCODED_COMPONENT_ORDER
from canonical.archivepublisher.diskpool import DiskPool
from canonical.archivepublisher.config import LucilleConfigError
from canonical.archivepublisher.domination import Dominator
from canonical.archivepublisher.ftparchive import FTPArchiveHandler
from canonical.archivepublisher.utils import (
    RepositoryIndexFile, get_ppa_reference)
from canonical.database.sqlbase import sqlvalues
from lp.soyuz.model.publishing import (
    SourcePackagePublishingHistory, BinaryPackagePublishingHistory)
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.binarypackagerelease import (
    BinaryPackageFormat)
from lp.soyuz.interfaces.archivesigningkey import (
    IArchiveSigningKey)
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.publishing import (
    pocketsuffix, PackagePublishingPocket, PackagePublishingStatus)

from canonical.librarian.client import LibrarianClient

suffixpocket = dict((v, k) for (k, v) in pocketsuffix.items())

DISTRORELEASE_STANZA = """Origin: %s
Label: %s
Suite: %s
Version: %s
Codename: %s
Date: %s
Architectures: %s
Components: %s
Description: %s
"""

DISTROARCHRELEASE_STANZA = """Archive: %s
Version: %s
Component: %s
Origin: %s
Label: %s
Architecture: %s
"""

class sha256:
    """Encapsulates apt_pkg.sha256sum as expected by publishing.

    It implements '__init__' and 'hexdigest' methods from PEP-247, which are
    the only ones required in soyuz-publishing-system.

    It's a work around for broken Crypto.Hash.SHA256. See further information
    in bug #131503.
    """
    def __init__(self, content):
        self._sum = apt_pkg.sha256sum(content)

    def hexdigest(self):
        """Return the hexdigest produced by apt_pkg.sha256sum."""
        return self._sum


def reorder_components(components):
    """Return a list of the components provided.

    The list will be ordered by the semi arbitrary rules of ubuntu.
    Over time this method needs to be removed and replaced by having
    component ordering codified in the database.
    """
    ret = []
    for comp in HARDCODED_COMPONENT_ORDER:
        if comp in components:
            ret.append(comp)
            components.remove(comp)
    ret.extend(components)
    return ret


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

def getPublisher(archive, allowed_suites, log, distsroot=None):
    """Return an initialised Publisher instance for the given context.

    The callsites can override the location where the archive indexes will
    be stored via 'distroot' argument.
    """
    if archive.purpose != ArchivePurpose.PPA:
        log.debug("Finding configuration for %s %s."
                  % (archive.distribution.name, archive.displayname))
    else:
        log.debug("Finding configuration for '%s' PPA."
                  % archive.owner.name)
    try:
        pubconf = archive.getPubConfig()
    except LucilleConfigError, info:
        log.error(info)
        raise

    # XXX cprov 2007-01-03: remove security proxy of the Config instance
    # returned by IArchive. This is kinda of a hack because Config doesn't
    # have any interface yet.
    pubconf = removeSecurityProxy(pubconf)
    disk_pool = _getDiskPool(pubconf, log)

    if distsroot is not None:
        log.debug("Overriding dists root with %s." % distsroot)
        pubconf.distsroot = distsroot

    log.debug("Preparing publisher.")

    return Publisher(log, pubconf, disk_pool, archive, allowed_suites)


class Publisher(object):
    """Publisher is the class used to provide the facility to publish
    files in the pool of a Distribution. The publisher objects will be
    instantiated by the archive build scripts and will be used throughout
    the processing of each DistroSeries and DistroArchSeries in question
    """

    def __init__(self, log, config, diskpool, archive, allowed_suites=None,
                 library=None):
        """Initialise a publisher.

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

        # Grab a reference to an apt_handler as we use it later to
        # probe which components need releases files generated.
        self.apt_handler = FTPArchiveHandler(self.log, self._config,
                                             self._diskpool, self.distro,
                                             self)
        # Track which distroseries pockets have been dirtied by a
        # change, and therefore need domination/apt-ftparchive work.
        # This is a set of tuples in the form (distroseries.name, pocket)
        self.dirty_pockets = set()

    def isDirty(self, distroseries, pocket):
        """True if a publication has happened in this release and pocket."""
        if not (distroseries.name, pocket) in self.dirty_pockets:
            return False
        return True

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
        if (self.allowed_suites and
            (distroseries.name, pocket) not in self.allowed_suites):
            return False
        return True

    def A_publish(self, force_publishing):
        """First step in publishing: actual package publishing.

        Asks each DistroSeries to publish itself, which causes
        publishing records to be updated, and files to be placed on disk
        where necessary.
        If self.allowed_suites is set, restrict the publication procedure
        to them.
        """
        self.log.debug("* Step A: Publishing packages")

        for distroseries in self.distro.serieses:
            for pocket, suffix in pocketsuffix.items():
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
        for distroseries in self.distro.serieses:
            for pocket, suffix in pocketsuffix.items():
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
        for distroseries in self.distro.serieses:
            for pocket in PackagePublishingPocket.items:
                if not force_domination:
                    if not self.isDirty(distroseries, pocket):
                        self.log.debug("Skipping domination for %s/%s" %
                                   (distroseries.name, pocket.name))
                        continue
                    self.checkDirtySuiteBeforePublishing(distroseries, pocket)
                judgejudy.judgeAndDominate(distroseries, pocket, self._config)

    def C_doFTPArchive(self, is_careful):
        """Does the ftp-archive step: generates Sources and Packages."""
        self.log.debug("* Step C: Set apt-ftparchive up and run it")
        self.apt_handler.run(is_careful)

    def C_writeIndexes(self, is_careful):
        """Write Index files (Packages & Sources) using LP information.

        Iterates over all distroserieses and its pockets and components.
        """
        self.log.debug("* Step C': write indexes directly from DB")
        for distroseries in self.distro:
            for pocket, suffix in pocketsuffix.items():
                if not is_careful:
                    if not self.isDirty(distroseries, pocket):
                        self.log.debug("Skipping index generation for %s/%s" %
                                       (distroseries.name, pocket.name))
                        continue
                    self.checkDirtySuiteBeforePublishing(distroseries, pocket)
                # Retrieve components from the publisher config because
                # it gets overridden in IArchive.getPubConfig to set the
                # correct components for the archive being used.
                for component_name in self._config.componentsForSeries(
                        distroseries.name):
                    component = getUtility(IComponentSet)[component_name]
                    self._writeComponentIndexes(
                        distroseries, pocket, component)

    def D_writeReleaseFiles(self, is_careful):
        """Write out the Release files for the provided distribution.

        If is_careful is specified, we include all pockets of all releases.

        Otherwise we include only pockets flagged as true in dirty_pockets.
        """
        self.log.debug("* Step D: Generating Release files.")
        for distroseries in self.distro:
            for pocket, suffix in pocketsuffix.items():

                if not is_careful:
                    if not self.isDirty(distroseries, pocket):
                        self.log.debug("Skipping release files for %s/%s" %
                                       (distroseries.name, pocket.name))
                        continue
                    self.checkDirtySuiteBeforePublishing(distroseries, pocket)
                self._writeDistroSeries(distroseries, pocket)

    def _writeComponentIndexes(self, distroseries, pocket, component):
        """Write Index files for single distroseries + pocket + component.

        Iterates over all supported architectures and 'sources', no
        support for installer-* yet.
        Write contents using LP info to an extra plain file (Packages.lp
        and Sources.lp .
        """
        suite_name = distroseries.name + pocketsuffix[pocket]
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
                if (bpp.binarypackagerelease.binpackageformat ==
                    BinaryPackageFormat.DEB):
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

        # Inject static requests for Release files into self.apt_handler
        # in a way which works for NoMoreAptFtpArchive without changing
        # much of the rest of the code, specially D_writeReleaseFiles.
        self.apt_handler.requestReleaseFile(
            suite_name, component.name, 'source')
        for arch in distroseries.architectures:
            arch_name = "binary-" + arch.architecturetag
            self.apt_handler.requestReleaseFile(
                suite_name, component.name, arch_name)

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
        if not self.archive.is_ppa:
            return self.distro.displayname
        return "LP-PPA-%s" % get_ppa_reference(self.archive)

    def _writeDistroSeries(self, distroseries, pocket):
        """Write out the Release files for the provided distroseries."""
        # XXX: kiko 2006-08-24: Untested method.

        # As we generate file lists for apt-ftparchive we record which
        # distroseriess and so on we need to generate Release files for.
        # We store this in release_files_needed and consume the information
        # when writeReleaseFiles is called.
        full_name = distroseries.name + pocketsuffix[pocket]
        release_files_needed = self.apt_handler.release_files_needed
        if full_name not in release_files_needed:
            # If we don't need to generate a release for this release
            # and pocket, don't!
            return

        all_components = set()
        all_architectures = set()
        all_files = set()
        release_files_needed_items = release_files_needed[full_name].items()
        for component, architectures in release_files_needed_items:
            all_components.add(component)
            for architecture in architectures:
                # XXX malcc 2006-09-20: We don't like the way we build this
                # all_architectures list. Make this better code.
                clean_architecture = self._writeDistroArchSeries(
                    distroseries, pocket, component, architecture, all_files)
                if clean_architecture != "source":
                    all_architectures.add(clean_architecture)

        drsummary = "%s %s " % (self.distro.displayname,
                                distroseries.displayname)
        if pocket == PackagePublishingPocket.RELEASE:
            drsummary += distroseries.version
        else:
            drsummary += pocket.name.capitalize()

        f = open(os.path.join(
            self._config.distsroot, full_name, "Release"), "w")

        stanza = DISTRORELEASE_STANZA % (
                    self._getOrigin(),
                    self.distro.displayname,
                    full_name,
                    distroseries.version,
                    distroseries.name,
                    datetime.utcnow().strftime("%a, %d %b %Y %k:%M:%S UTC"),
                    " ".join(sorted(list(all_architectures))),
                    " ".join(reorder_components(all_components)), drsummary)
        f.write(stanza)

        f.write("MD5Sum:\n")
        all_files = sorted(list(all_files), key=os.path.dirname)
        for file_name in all_files:
            self._writeSumLine(full_name, f, file_name, md5)
        f.write("SHA1:\n")
        for file_name in all_files:
            self._writeSumLine(full_name, f, file_name, sha)
        f.write("SHA256:\n")
        for file_name in all_files:
            self._writeSumLine(full_name, f, file_name, sha256)

        f.close()

        # Skip signature if the archive signing key is undefined.
        if self.archive.signing_key is None:
            self.log.debug("No signing key available, skipping signature.")
            return

        # Sign the repository.
        archive_signer = IArchiveSigningKey(self.archive)
        archive_signer.signRepository(full_name)

    def _writeDistroArchSeries(self, distroseries, pocket, component,
                                architecture, all_files):
        """Write out a Release file for a DAR."""
        # XXX kiko 2006-08-24: Untested method.

        full_name = distroseries.name + pocketsuffix[pocket]
        index_suffixes = ('', '.gz', '.bz2')

        self.log.debug("Writing Release file for %s/%s/%s" % (
            full_name, component, architecture))

        if architecture != "source":
            # Strip "binary-" off the front of the architecture
            clean_architecture = architecture[7:]
            file_stub = "Packages"

            # Only the primary and PPA archives have debian-installer.
            if self.archive.purpose != ArchivePurpose.PARTNER:
                # Set up the debian-installer paths for main_archive.
                # d-i paths are nested inside the component.
                di_path = os.path.join(
                    component, "debian-installer", architecture)
                di_file_stub = os.path.join(di_path, file_stub)
                for suffix in index_suffixes:
                    all_files.add(di_file_stub + suffix)
        else:
            file_stub = "Sources"
            clean_architecture = architecture

        # Now, grab the actual (non-di) files inside each of
        # the suite's architectures
        file_stub = os.path.join(component, architecture, file_stub)

        for suffix in index_suffixes:
            all_files.add(file_stub + suffix)

        all_files.add(os.path.join(component, architecture, "Release"))

        f = open(os.path.join(self._config.distsroot, full_name,
                              component, architecture, "Release"), "w")

        stanza = DISTROARCHRELEASE_STANZA % (
                full_name,
                distroseries.version,
                component,
                self._getOrigin(),
                self.distro.displayname,
                clean_architecture)
        f.write(stanza)
        f.close()

        return clean_architecture

    def _writeSumLine(self, distroseries_name, out_file, file_name, sum_form):
        """Write out a checksum line.

        Writes a checksum to the given file for the given filename in
        the given form.
        """
        full_name = os.path.join(self._config.distsroot,
                                 distroseries_name, file_name)
        if not os.path.exists(full_name):
            # The file we were asked to write out doesn't exist.
            # Most likely we have an incomplete archive (E.g. no sources
            # for a given distroseries). This is a non-fatal issue
            self.log.debug("Failed to find " + full_name)
            return

        in_file = open(full_name, 'r')
        try:
            # XXX cprov 20080704 bug=243630,269014: Workaround for hardy's
            # python-apt. If it receives a file object as an argument instead
            # of the file contents as a string, it will generate the correct
            # SHA256.
            if sum_form == sha256:
                contents = in_file
                length = os.stat(full_name).st_size
            else:
                contents = in_file.read()
                length = len(contents)
            checksum = sum_form(contents).hexdigest()
        finally:
            in_file.close()

        out_file.write(" %s % 16d %s\n" % (checksum, length, file_name))
