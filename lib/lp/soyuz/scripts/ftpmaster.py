# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""FTPMaster utilities."""

__metaclass__ = type

__all__ = [
    'ArchiveCruftChecker',
    'ArchiveCruftCheckerError',
    'ChrootManager',
    'ChrootManagerError',
    'LpQueryDistro',
    'ManageChrootScript',
    'ObsoleteDistroseries',
    'PackageRemover',
    'PubSourceChecker',
    'SyncSource',
    'SyncSourceError',
    ]

import commands
import hashlib
import os
import stat
import sys
import tempfile
import time

import apt_pkg
from debian.deb822 import Changes
from zope.component import getUtility

from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.librarian.interfaces import (
    ILibrarianClient,
    UploadFailed,
    )
from canonical.librarian.utils import copy_and_close
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.archiveuploader.utils import (
    determine_source_file_type,
    re_extract_src_version,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.sourcepackage import SourcePackageFileType
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )
from lp.soyuz.adapters.packagelocation import (
    build_package_location,
    PackageLocationError,
    )
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageNameSet
from lp.soyuz.scripts.ftpmasterbase import (
    SoyuzScript,
    SoyuzScriptError,
    )


class ArchiveCruftCheckerError(Exception):
    """ArchiveCruftChecker specific exception.

    Mostly used to describe errors in the initialization of this object.
    """


class TagFileNotFound(Exception):
    """Raised when an archive tag file could not be found."""


class ArchiveCruftChecker:
    """Perform overall checks to identify and remove obsolete records.

    Use initialize() method to validate passed parameters and build the
    infrastructure variables. It will raise ArchiveCruftCheckerError if
    something goes wrong.
    """

    # XXX cprov 2006-05-15: the default archive path should come
    # from the config.
    def __init__(self, logger, distribution_name='ubuntu', suite=None,
                 archive_path='/srv/launchpad.net/ubuntu-archive'):
        """Store passed arguments.

        Also Initialize empty variables for storing preliminar results.
        """
        self.distribution_name = distribution_name
        self.suite = suite
        self.archive_path = archive_path
        self.logger = logger
        # initialize a group of variables to store temporary results
        # available versions of published sources
        self.source_versions = {}
        # available binaries produced by published sources
        self.source_binaries = {}
        # 'Not Build From Source' binaries
        self.nbs = {}
        # 'All superseded by Any' binaries
        self.asba = {}
        # published binary package names
        self.bin_pkgs = {}
        # Architecture specific binary packages
        self.arch_any = {}
        # proposed NBS (before clean up)
        self.dubious_nbs = {}
        # NBS after clean up
        self.real_nbs = {}
        # definitive NBS organized for clean up
        self.nbs_to_remove = []

    @property
    def architectures(self):
        return dict([(a.architecturetag, a)
                     for a in self.distroseries.architectures])

    @property
    def components(self):
        return dict([(c.name, c) for c in self.distroseries.components])

    @property
    def components_and_di(self):
        components_and_di = []
        for component in self.components:
            components_and_di.append(component)
            components_and_di.append('%s/debian-installer' % (component))
        return components_and_di

    @property
    def dist_archive(self):
        return os.path.join(
            self.archive_path, self.distro.name, 'dists',
            self.distroseries.name + pocketsuffix[self.pocket])

    def gunzipTagFileContent(self, filename):
        """Gunzip the contents of passed filename.

        Check filename presence, if not present in the filesystem,
        raises ArchiveCruftCheckerError. Use an tempfile.mkstemp()
        to store the uncompressed content. Invoke system available
        gunzip`, raises ArchiveCruftCheckError if it fails.

        This method doesn't close the file descriptor used and does not
        remove the temporary file from the filesystem, those actions
        are required in the callsite. (apt_pkg.ParseTagFile is lazy)

        Return a tuple containing:
         * temp file descriptor
         * temp filename
         * the contents parsed by apt_pkg.ParseTagFile()
        """
        if not os.path.exists(filename):
            raise TagFileNotFound("File does not exist: %s" % filename)

        temp_fd, temp_filename = tempfile.mkstemp()
        (result, output) = commands.getstatusoutput(
            "gunzip -c %s > %s" % (filename, temp_filename))
        if result != 0:
            raise ArchiveCruftCheckerError(
                "Gunzip invocation failed!\n%s" % output)

        temp_file = os.fdopen(temp_fd)
        # XXX cprov 2006-05-15: maybe we need some sort of data integrity
        # check at this point, and maybe keep the uncrompressed file
        # for debug purposes, let's see how it behaves in real conditions.
        parsed_contents = apt_pkg.ParseTagFile(temp_file)

        return temp_file, temp_filename, parsed_contents

    def processSources(self):
        """Process archive sources index.

        Build source_binaries, source_versions and bin_pkgs lists.
        """
        self.logger.debug("Considering Sources:")
        for component in self.components:
            filename = os.path.join(
                self.dist_archive, "%s/source/Sources.gz" % component)

            self.logger.debug("Processing %s" % filename)
            try:
                temp_fd, temp_filename, parsed_sources = (
                    self.gunzipTagFileContent(filename))
            except TagFileNotFound, warning:
                self.logger.warn(warning)
                return
            try:
                while parsed_sources.Step():
                    source = parsed_sources.Section.Find("Package")
                    source_version = parsed_sources.Section.Find("Version")
                    architecture = parsed_sources.Section.Find("Architecture")
                    binaries = parsed_sources.Section.Find("Binary")
                    for binary in [
                        item.strip() for item in binaries.split(',')]:
                        self.bin_pkgs.setdefault(binary, [])
                        self.bin_pkgs[binary].append(source)

                    self.source_binaries[source] = binaries
                    self.source_versions[source] = source_version
            finally:
                # close fd and remove temporary file used to store
                # uncompressed tag file content from the filesystem.
                temp_fd.close()
                os.unlink(temp_filename)

    def buildNBS(self):
        """Build the group of 'not build from source' binaries"""
        # Checks based on the Packages files
        self.logger.debug("Building not build from source list (NBS):")
        for component in self.components_and_di:
            for architecture in self.architectures:
                self.buildArchNBS(component, architecture)

    def buildArchNBS(self, component, architecture):
        """Build NBS per architecture.

        Store results in self.nbs, also build architecture specific
        binaries group (stored in self.arch_any)
        """
        filename = os.path.join(
            self.dist_archive,
            "%s/binary-%s/Packages.gz" % (component, architecture))

        self.logger.debug("Processing %s" % filename)
        try:
            temp_fd, temp_filename, parsed_packages = (
                self.gunzipTagFileContent(filename))
        except TagFileNotFound, warning:
            self.logger.warn(warning)
            return

        try:
            while parsed_packages.Step():
                package = parsed_packages.Section.Find('Package')
                source = parsed_packages.Section.Find('Source', "")
                version = parsed_packages.Section.Find('Version')
                architecture = parsed_packages.Section.Find('Architecture')

                if source == "":
                    source = package

                if source.find("(") != -1:
                    m = re_extract_src_version.match(source)
                    source = m.group(1)
                    version = m.group(2)

                if package not in self.bin_pkgs:
                    self.nbs.setdefault(source, {})
                    self.nbs[source].setdefault(package, {})
                    self.nbs[source][package][version] = ""

                if architecture != "all":
                    self.arch_any.setdefault(package, "0")
                    if apt_pkg.VersionCompare(
                        version, self.arch_any[package]) < 1:
                        self.arch_any[package] = version
        finally:
            # close fd and remove temporary file used to store uncompressed
            # tag file content from the filesystem.
            temp_fd.close()
            os.unlink(temp_filename)

    def buildASBA(self):
        """Build the group of 'all superseded by any' binaries."""
        self.logger.debug("Building all superseded by any list (ASBA):")
        for component in self.components_and_di:
            for architecture in self.architectures:
                self.buildArchASBA(component, architecture)

    def buildArchASBA(self, component, architecture):
        """Build ASBA per architecture.

        Store the result in self.asba, require self.arch_any to be built
        previously.
        """
        filename = os.path.join(
            self.dist_archive,
            "%s/binary-%s/Packages.gz" % (component, architecture))

        try:
            temp_fd, temp_filename, parsed_packages = (
                self.gunzipTagFileContent(filename))
        except TagFileNotFound, warning:
            self.logger.warn(warning)
            return

        try:
            while parsed_packages.Step():
                package = parsed_packages.Section.Find('Package')
                source = parsed_packages.Section.Find('Source', "")
                version = parsed_packages.Section.Find('Version')
                architecture = parsed_packages.Section.Find('Architecture')

                if source == "":
                    source = package

                if source.find("(") != -1:
                    m = re_extract_src_version.match(source)
                    source = m.group(1)
                    version = m.group(2)

                if architecture == "all":
                    if (package in self.arch_any and
                        apt_pkg.VersionCompare(
                        version, self.arch_any[package]) > -1):
                        self.asba.setdefault(source, {})
                        self.asba[source].setdefault(package, {})
                        self.asba[source][package].setdefault(version, {})
                        self.asba[source][package][version][architecture] = ""
        finally:
            # close fd and remove temporary file used to store uncompressed
            # tag file content from the filesystem.
            temp_fd.close()
            os.unlink(temp_filename)

    def addNBS(self, nbs_d, source, version, package):
        """Add a new entry in given organized nbs_d list

        Ensure the package is still published in the suite before add.
        """
        result = self.distroseries.getBinaryPackagePublishing(name=package)

        if len(list(result)) == 0:
            return

        nbs_d.setdefault(source, {})
        nbs_d[source].setdefault(version, {})
        nbs_d[source][version][package] = ""

    def refineNBS(self):
        """ Distinguish dubious from real NBS.

        They are 'dubious' if the version numbers match and 'real'
        if the versions don't match.
        It stores results in self.dubious_nbs and self.real_nbs.
        """
        for source in self.nbs.keys():
            for package in self.nbs[source].keys():
                versions = self.nbs[source][package].keys()
                versions.sort(apt_pkg.VersionCompare)
                latest_version = versions.pop()

                source_version = self.source_versions.get(source, "0")

                if apt_pkg.VersionCompare(latest_version,
                                          source_version) == 0:
                    self.addNBS(self.dubious_nbs, source, latest_version,
                                package)
                else:
                    self.addNBS(self.real_nbs, source, latest_version,
                                package)

    def outputNBS(self):
        """Properly display built NBS entries.

        Also organize the 'real' NBSs for removal in self.nbs_to_remove
        attribute.
        """
        output = "Not Built from Source\n"
        output += "---------------------\n\n"

        nbs_keys = self.real_nbs.keys()
        nbs_keys.sort()

        for source in nbs_keys:
            proposed_bin = self.source_binaries.get(
                source, "(source does not exist)")
            porposed_version = self.source_versions.get(source, "??")
            output += (" * %s_%s builds: %s\n"
                       % (source, porposed_version, proposed_bin))
            output += "\tbut no longer builds:\n"
            versions = self.real_nbs[source].keys()
            versions.sort(apt_pkg.VersionCompare)

            for version in versions:
                packages = self.real_nbs[source][version].keys()
                packages.sort()

                for pkg in packages:
                    self.nbs_to_remove.append(pkg)

                output += "        o %s: %s\n" % (
                    version, ", ".join(packages))

            output += "\n"

        if self.nbs_to_remove:
            self.logger.info(output)
        else:
            self.logger.debug("No NBS found")

    def initialize(self):
        """Initialize and build required lists of obsolete entries in archive.

        Check integrity of passed parameters and store organised data.
        The result list is the self.nbs_to_remove which should contain
        obsolete packages not currently able to be built from again.
        Another preliminary lists can be inspected in order to have better
        idea of what was computed.
        If anything goes wrong mid-process, it raises ArchiveCruftCheckError,
        otherwise a list of packages to be removes is printed.
        """
        if self.distribution_name is None:
            self.distro = getUtility(ILaunchpadCelebrities).ubuntu
        else:
            try:
                self.distro = getUtility(IDistributionSet)[
                    self.distribution_name]
            except NotFoundError:
                raise ArchiveCruftCheckerError(
                    "Invalid distribution: '%s'" % self.distribution_name)

        if not self.suite:
            self.distroseries = self.distro.currentseries
            self.pocket = PackagePublishingPocket.RELEASE
        else:
            try:
                self.distroseries, self.pocket = (
                    self.distro.getDistroSeriesAndPocket(self.suite))
            except NotFoundError:
                raise ArchiveCruftCheckerError(
                    "Invalid suite: '%s'" % self.suite)

        if not os.path.exists(self.dist_archive):
            raise ArchiveCruftCheckerError(
                "Invalid archive path: '%s'" % self.dist_archive)

        apt_pkg.init()
        self.processSources()
        self.buildNBS()
        self.buildASBA()
        self.refineNBS()
        self.outputNBS()

    def doRemovals(self):
        """Perform the removal of the obsolete packages found.

        It iterates over the previously build list (self.nbs_to_remove)
        and mark them as 'superseded' in the archive DB model. They will
        get removed later by the archive sanity check run each cycle
        of the cron.daily.
        """
        for package in self.nbs_to_remove:

            for distroarchseries in self.distroseries.architectures:
                binarypackagename = getUtility(IBinaryPackageNameSet)[package]
                dasbp = distroarchseries.getBinaryPackage(binarypackagename)
                dasbpr = dasbp.currentrelease
                try:
                    bpph = dasbpr.current_publishing_record
                    bpph.supersede()
                    # We're blindly removing for all arches, if it's not there
                    # for some, that's fine ...
                except NotFoundError:
                    pass
                else:
                    version = bpph.binarypackagerelease.version
                    self.logger.info("Removed %s_%s from %s/%s ... "
                                      % (package, version,
                                         self.distroseries.name,
                                         distroarchseries.architecturetag))


class PubBinaryContent:
    """Binary publication container.

    Currently used for auxiliary storage in PubSourceChecker.
    """

    def __init__(self, name, version, arch, component, section, priority):
        self.name = name
        self.version = version
        self.arch = arch
        self.component = component
        self.section = section
        self.priority = priority
        self.messages = []

    def warn(self, message):
        """Append a warning in the message list."""
        self.messages.append('W: %s' % message)

    def error(self, message):
        """Append a error in the message list."""
        self.messages.append('E: %s' % message)

    def renderReport(self):
        """Render a report with the appended messages (self.messages).

        Return None if no message was found, otherwise return
        a properly formatted string, including

        <TAB>BinaryName_Version Arch Component/Section/Priority
        <TAB><TAB>MESSAGE
        """
        if not len(self.messages):
            return

        report = [('\t%s_%s %s %s/%s/%s'
                   % (self.name, self.version, self.arch,
                      self.component, self.section, self.priority))]

        for message in self.messages:
            report.append('\t\t%s' % message)

        return "\n".join(report)


class PubBinaryDetails:
    """Store the component, section and priority of binary packages and, for
    each binary package the most frequent component, section and priority.

    These are stored in the following attributes:

    - components: A dictionary mapping binary package names to other
      dictionaries mapping component names to binary packages published
      in this component.
    - sections: The same as components, but for sections.
    - priorities: The same as components, but for priorities.
    - correct_components: a dictionary mapping binary package name
      to the most frequent (considered the correct) component name.
    - correct_sections: same as correct_components, but for sections
    - correct_priorities: same as correct_components, but for priorities
    """

    def __init__(self):
        self.components = {}
        self.sections = {}
        self.priorities = {}
        self.correct_components = {}
        self.correct_sections = {}
        self.correct_priorities = {}

    def addBinaryDetails(self, bin):
        """Include a binary publication and update internal registers."""
        name_components = self.components.setdefault(bin.name, {})
        bin_component = name_components.setdefault(bin.component, [])
        bin_component.append(bin)

        name_sections = self.sections.setdefault(bin.name, {})
        bin_section = name_sections.setdefault(bin.section, [])
        bin_section.append(bin)

        name_priorities = self.priorities.setdefault(bin.name, {})
        bin_priority = name_priorities.setdefault(bin.priority, [])
        bin_priority.append(bin)

    def _getMostFrequentValue(self, data):
        """Return a dict of name and the most frequent value.

        Used for self.{components, sections, priorities}
        """
        results = {}

        for name, items in data.iteritems():
            highest = 0
            for item, occurrences in items.iteritems():
                if len(occurrences) > highest:
                    highest = len(occurrences)
                    results[name] = item

        return results

    def setCorrectValues(self):
        """Find out the correct values for the same binary name

        Consider correct the most frequent.
        """
        self.correct_components = self._getMostFrequentValue(self.components)
        self.correct_sections = self._getMostFrequentValue(self.sections)
        self.correct_priorities = self._getMostFrequentValue(self.priorities)


class PubSourceChecker:
    """Map and probe a Source/Binaries publication couple.

    Receive the source publication data and its binaries and perform
    a group of heuristic consistency checks.
    """

    def __init__(self, name, version, component, section, urgency):
        self.name = name
        self.version = version
        self.component = component
        self.section = section
        self.urgency = urgency
        self.binaries = []
        self.binaries_details = PubBinaryDetails()

    def addBinary(self, name, version, architecture, component, section,
                  priority):
        """Append the binary data to the current publication list."""
        bin = PubBinaryContent(
            name, version, architecture, component, section, priority)

        self.binaries.append(bin)

        self.binaries_details.addBinaryDetails(bin)

    def check(self):
        """Setup check environment and perform the required checks."""
        self.binaries_details.setCorrectValues()

        for bin in self.binaries:
            self._checkComponent(bin)
            self._checkSection(bin)
            self._checkPriority(bin)

    def _checkComponent(self, bin):
        """Check if the binary component matches the correct component.

        'correct' is the most frequent component in this binary package
        group
        """
        correct_component = self.binaries_details.correct_components[bin.name]
        if bin.component != correct_component:
            bin.warn('Component mismatch: %s != %s'
                     % (bin.component, correct_component))

    def _checkSection(self, bin):
        """Check if the binary section matches the correct section.

        'correct' is the most frequent section in this binary package
        group
        """
        correct_section = self.binaries_details.correct_sections[bin.name]
        if bin.section != correct_section:
            bin.warn('Section mismatch: %s != %s'
                     % (bin.section, correct_section))

    def _checkPriority(self, bin):
        """Check if the binary priority matches the correct priority.

        'correct' is the most frequent priority in this binary package
        group
        """
        correct_priority = self.binaries_details.correct_priorities[bin.name]
        if bin.priority != correct_priority:
            bin.warn('Priority mismatch: %s != %s'
                     % (bin.priority, correct_priority))

    def renderReport(self):
        """Render a formatted report for the publication group.

        Return None if no issue was annotated or an formatted string
        including:

          SourceName_Version Component/Section/Urgency | # bin
          <BINREPORTS>
        """
        report = []

        for bin in self.binaries:
            bin_report = bin.renderReport()
            if bin_report:
                report.append(bin_report)

        if not len(report):
            return

        result = [('%s_%s %s/%s/%s | %s bin'
                   % (self.name, self.version, self.component,
                      self.section, self.urgency, len(self.binaries)))]

        result.extend(report)

        return "\n".join(result)


class ChrootManagerError(Exception):
    """Any error generated during the ChrootManager procedures."""


class ChrootManager:
    """Chroot actions wrapper.

    The 'distroarchseries' argument is mandatory and 'filepath' is
    optional.

    'filepath' is required by some allowed actions as source or destination,

    ChrootManagerError will be raised if anything wrong occurred in this
    class, things like missing parameter or infrastructure pieces not in
    place.
    """

    allowed_actions = ['add', 'update', 'remove', 'get']

    def __init__(self, distroarchseries, filepath=None):
        self.distroarchseries = distroarchseries
        self.filepath = filepath
        self._messages = []

    def _upload(self):
        """Upload the self.filepath contents to Librarian.

        Return the respective ILibraryFileAlias instance.
        Raises ChrootManagerError if it could not be found.
        """
        try:
            fd = open(self.filepath)
        except IOError:
            raise ChrootManagerError('Could not open: %s' % self.filepath)

        flen = os.stat(self.filepath).st_size
        filename = os.path.basename(self.filepath)
        ftype = filenameToContentType(filename)

        try:
            alias_id = getUtility(ILibrarianClient).addFile(
                filename, flen, fd, contentType=ftype)
        except UploadFailed, info:
            raise ChrootManagerError("Librarian upload failed: %s" % info)

        lfa = getUtility(ILibraryFileAliasSet)[alias_id]

        self._messages.append(
            "LibraryFileAlias: %d, %s bytes, %s"
            % (lfa.id, lfa.content.filesize, lfa.content.md5))

        return lfa

    def _getPocketChroot(self):
        """Retrive PocketChroot record.

        Return the respective IPocketChroot instance.
        Raises ChrootManagerError if it could not be found.
        """
        pocket_chroot = self.distroarchseries.getPocketChroot()
        if pocket_chroot is None:
            raise ChrootManagerError(
                'Could not find chroot for %s'
                % (self.distroarchseries.title))

        self._messages.append(
            "PocketChroot for '%s' (%d) retrieved."
            % (pocket_chroot.distroarchseries.title, pocket_chroot.id))

        return pocket_chroot

    def _update(self):
        """Base method for add and update action."""
        if self.filepath is None:
            raise ChrootManagerError('Missing local chroot file path.')
        alias = self._upload()
        return self.distroarchseries.addOrUpdateChroot(alias)

    def add(self):
        """Create a new PocketChroot record.

        Raises ChrootManagerError if self.filepath isn't set.
        Update of pre-existing PocketChroot record will be automatically
        handled.
        It's a bind to the self.update method.
        """
        pocket_chroot = self._update()
        self._messages.append(
            "PocketChroot for '%s' (%d) added."
            % (pocket_chroot.distroarchseries.title, pocket_chroot.id))

    def update(self):
        """Update a PocketChroot record.

        Raises ChrootManagerError if filepath isn't set
        Creation of non-existing PocketChroot records will be automatically
        handled.
        """
        pocket_chroot = self._update()
        self._messages.append(
            "PocketChroot for '%s' (%d) updated."
            % (pocket_chroot.distroarchseries.title, pocket_chroot.id))

    def remove(self):
        """Overwrite existing PocketChroot file to none.

        Raises ChrootManagerError if the chroot record isn't found.
        """
        pocket_chroot = self._getPocketChroot()
        self.distroarchseries.addOrUpdateChroot(None)
        self._messages.append(
            "PocketChroot for '%s' (%d) removed."
            % (pocket_chroot.distroarchseries.title, pocket_chroot.id))

    def get(self):
        """Download chroot file from Librarian and store."""
        pocket_chroot = self._getPocketChroot()

        if self.filepath is None:
            abs_filepath = os.path.abspath(pocket_chroot.chroot.filename)
            if os.path.exists(abs_filepath):
                raise ChrootManagerError(
                    'cannot overwrite %s' % abs_filepath)
            self._messages.append(
                "Writing to '%s'." % abs_filepath)
            local_file = open(pocket_chroot.chroot.filename, "w")
        else:
            abs_filepath = os.path.abspath(self.filepath)
            if os.path.exists(abs_filepath):
                raise ChrootManagerError(
                    'cannot overwrite %s' % abs_filepath)
            self._messages.append(
                "Writing to '%s'." % abs_filepath)
            local_file = open(abs_filepath, "w")

        if pocket_chroot.chroot is None:
            raise ChrootManagerError('Chroot was deleted.')

        pocket_chroot.chroot.open()
        copy_and_close(pocket_chroot.chroot, local_file)


class SyncSourceError(Exception):
    """Raised when an critical error occurs inside SyncSource.

    The entire procedure should be aborted in order to avoid unknown problems.
    """


class SyncSource:
    """Sync Source procedure helper class.

    It provides the backend for retrieving files from Librarian or the
    'sync source' location. Also provides a method to check the downloaded
    files integrity.
    'aptMD5Sum' is provided as a classmethod during the integration time.
    """

    def __init__(self, files, origin, logger, downloader, todistro):
        """Store local context.

        files: a dictionary where the keys are the filename and the
               value another dictionary with the file informations.
        origin: a dictionary similar to 'files' but where the values
                contain information for download files to be synchronized
        logger: a logger
        downloader: a callable that fetchs URLs,
                    'downloader(url, destination)'
        todistro: target distribution object
        """
        self.files = files
        self.origin = origin
        self.logger = logger
        self.downloader = downloader
        self.todistro = todistro

    @classmethod
    def generateMD5Sum(self, filename):
        file_handle = open(filename)
        md5sum = hashlib.md5(file_handle.read()).hexdigest()
        file_handle.close()
        return md5sum

    def fetchFileFromLibrarian(self, filename):
        """Fetch file from librarian.

        Store the contents in local path with the original filename.
        Return the fetched filename if it was present in Librarian or None
        if it wasn't.
        """
        try:
            libraryfilealias = self.todistro.main_archive.getFileByName(
                filename)
        except NotFoundError:
            return None

        self.logger.info(
            "%s: already in distro - downloading from librarian" %
            filename)

        output_file = open(filename, 'w')
        libraryfilealias.open()
        copy_and_close(libraryfilealias, output_file)
        return filename

    def fetchLibrarianFiles(self):
        """Try to fetch files from Librarian.

        It raises SyncSourceError if anything else then an
        orig tarball was found in Librarian.
        Return the names of the files retrieved from the librarian.
        """
        retrieved = []
        for filename in self.files.keys():
            if not self.fetchFileFromLibrarian(filename):
                continue
            file_type = determine_source_file_type(filename)
            # set the return code if an orig was, in fact,
            # fetched from Librarian
            if not file_type in (SourcePackageFileType.ORIG_TARBALL,
                                 SourcePackageFileType.COMPONENT_ORIG_TARBALL):
                raise SyncSourceError(
                    'Oops, only orig tarball can be retrieved from librarian.')
            retrieved.append(filename)

        return retrieved

    def fetchSyncFiles(self):
        """Fetch files from the original sync source.

        Return DSC filename, which should always come via this path.
        """
        dsc_filename = None
        for filename in self.files.keys():
            file_type = determine_source_file_type(filename)
            if file_type == SourcePackageFileType.DSC:
                dsc_filename = filename
            if os.path.exists(filename):
                self.logger.info("  - <%s: cached>" % (filename))
                continue
            self.logger.info(
                "  - <%s: downloading from %s>" %
                (filename, self.origin["url"]))
            download_f = ("%s%s" % (self.origin["url"],
                                    self.files[filename]["remote filename"]))
            sys.stdout.flush()
            self.downloader(download_f, filename)
        return dsc_filename

    def checkDownloadedFiles(self):
        """Check md5sum and size match Source.

        If anything fails SyncSourceError will be raised.
        """
        for filename in self.files.keys():
            actual_md5sum = self.generateMD5Sum(filename)
            expected_md5sum = self.files[filename]["md5sum"]
            if actual_md5sum != expected_md5sum:
                raise SyncSourceError(
                    "%s: md5sum check failed (%s [actual] "
                    "vs. %s [expected])."
                    % (filename, actual_md5sum, expected_md5sum))

            actual_size = os.stat(filename)[stat.ST_SIZE]
            expected_size = int(self.files[filename]["size"])
            if actual_size != expected_size:
                raise SyncSourceError(
                    "%s: size mismatch (%s [actual] vs. %s [expected])."
                    % (filename, actual_size, expected_size))


class LpQueryDistro(LaunchpadScript):
    """Main class for scripts/ftpmaster-tools/lp-query-distro.py."""

    def __init__(self, *args, **kwargs):
        """Initialize dynamic 'usage' message and LaunchpadScript parent.

        Also initialize the list 'allowed_arguments'.
        """
        self.allowed_actions = [
            'current', 'development', 'supported', 'pending_suites', 'archs',
            'official_archs', 'nominated_arch_indep', 'pocket_suffixes']
        self.usage = '%%prog <%s>' % ' | '.join(self.allowed_actions)
        LaunchpadScript.__init__(self, *args, **kwargs)

    def add_my_options(self):
        """Add 'distribution' and 'suite' context options."""
        self.parser.add_option(
            '-d', '--distribution', dest='distribution_name',
            default='ubuntu', help='Context distribution name.')
        self.parser.add_option(
            '-s', '--suite', dest='suite', default=None,
            help='Context suite name.')

    def main(self):
        """Main procedure, basically a runAction wrapper.

        Execute the given and allowed action using the default presenter
        (see self.runAction for further information).
        """
        self.runAction()

    def _buildLocation(self):
        """Build a PackageLocation object

        The location will correspond to the given 'distribution' and 'suite',
        Any PackageLocationError occurring at this point will be masked into
        LaunchpadScriptFailure.
        """
        try:
            self.location = build_package_location(
                distribution_name=self.options.distribution_name,
                suite=self.options.suite)
        except PackageLocationError, err:
            raise LaunchpadScriptFailure(err)

    def defaultPresenter(self, result):
        """Default result presenter.

        Directly prints result in the standard output (print).
        """
        print result

    def runAction(self, presenter=None):
        """Run a given initialized action (self.action_name).

        It accepts an optional 'presenter' which will be used to
        store/present the action result.

        Ensure at least one argument was passed, known as 'action'.
        Verify if the given 'action' is listed as an 'allowed_action'.
        Raise LaunchpadScriptFailure if those requirements were not
        accomplished.

        It builds context 'location' object (see self._buildLocation).

        It may raise LaunchpadScriptFailure is the 'action' is not properly
        supported by the current code (missing corresponding property).
        """
        if presenter is None:
            presenter = self.defaultPresenter

        if len(self.args) != 1:
            raise LaunchpadScriptFailure('<action> is required')

        [self.action_name] = self.args

        if self.action_name not in self.allowed_actions:
            raise LaunchpadScriptFailure(
                'Action "%s" is not supported' % self.action_name)

        self._buildLocation()

        try:
            action_result = getattr(self, self.action_name)
        except AttributeError:
            raise AssertionError(
                "No handler found for action '%s'" % self.action_name)

        presenter(action_result)

    def checkNoSuiteDefined(self):
        """Raises LaunchpadScriptError if a suite location was passed.

        It is re-used in action properties to avoid conflicting contexts,
        i.e, passing an arbitrary 'suite' and asking for the CURRENT suite
        in the context distribution.
        """
        if self.options.suite is not None:
            raise LaunchpadScriptFailure(
                "Action does not accept defined suite.")

    @property
    def current(self):
        """Return the name of the CURRENT distroseries.

        It is restricted for the context distribution.

        It may raise LaunchpadScriptFailure if a suite was passed on the
        command-line or if not CURRENT distroseries was found.
        """
        self.checkNoSuiteDefined()
        series = self.location.distribution.getSeriesByStatus(
            SeriesStatus.CURRENT)
        if not series:
            raise LaunchpadScriptFailure("No CURRENT series.")

        return series[0].name

    @property
    def development(self):
        """Return the name of the DEVELOPMENT distroseries.

        It is restricted for the context distribution.

        It may raise `LaunchpadScriptFailure` if a suite was passed on the
        command-line.

        Return the first FROZEN distroseries found if there is no
        DEVELOPMENT one available.

        Raises `NotFoundError` if neither a CURRENT nor a FROZEN
        candidate could be found.
        """
        self.checkNoSuiteDefined()
        series = None
        wanted_status = (SeriesStatus.DEVELOPMENT,
                         SeriesStatus.FROZEN)
        for status in wanted_status:
            series = self.location.distribution.getSeriesByStatus(status)
            if series.count() > 0:
                break
        else:
            raise LaunchpadScriptFailure(
                'There is no DEVELOPMENT distroseries for %s' %
                self.location.distribution.name)
        return series[0].name

    @property
    def supported(self):
        """Return the names of the distroseries currently supported.

        'supported' means not EXPERIMENTAL or OBSOLETE.

        It is restricted for the context distribution.

        It may raise `LaunchpadScriptFailure` if a suite was passed on the
        command-line or if there is not supported distroseries for the
        distribution given.

        Return a space-separated list of distroseries names.
        """
        self.checkNoSuiteDefined()
        supported_series = []
        unsupported_status = (SeriesStatus.EXPERIMENTAL,
                              SeriesStatus.OBSOLETE)
        for distroseries in self.location.distribution:
            if distroseries.status not in unsupported_status:
                supported_series.append(distroseries.name)

        if not supported_series:
            raise LaunchpadScriptFailure(
                'There is no supported distroseries for %s' %
                self.location.distribution.name)

        return " ".join(supported_series)

    @property
    def pending_suites(self):
        """Return the suite names containing PENDING publication.

        It check for sources and/or binary publications.
        """
        self.checkNoSuiteDefined()
        pending_suites = set()
        pending_sources = self.location.archive.getPublishedSources(
            status=PackagePublishingStatus.PENDING)
        for pub in pending_sources:
            pending_suites.add((pub.distroseries, pub.pocket))

        pending_binaries = self.location.archive.getAllPublishedBinaries(
            status=PackagePublishingStatus.PENDING)
        for pub in pending_binaries:
            pending_suites.add(
                (pub.distroarchseries.distroseries, pub.pocket))

        return " ".join([distroseries.name + pocketsuffix[pocket]
                         for distroseries, pocket in pending_suites])

    @property
    def archs(self):
        """Return a space-separated list of architecture tags.

        It is restricted for the context distribution and suite.
        """
        architectures = self.location.distroseries.architectures
        return " ".join(arch.architecturetag for arch in architectures)

    @property
    def official_archs(self):
        """Return a space-separated list of official architecture tags.

        It is restricted to the context distribution and suite.
        """
        architectures = self.location.distroseries.architectures
        return " ".join(arch.architecturetag
                        for arch in architectures
                        if arch.official)

    @property
    def nominated_arch_indep(self):
        """Return the nominated arch indep architecture tag.

        It is restricted to the context distribution and suite.
        """
        series = self.location.distroseries
        return series.nominatedarchindep.architecturetag

    @property
    def pocket_suffixes(self):
        """Return a space-separated list of non-empty pocket suffixes.

        The RELEASE pocket (whose suffix is the empty string) is omitted.

        The returned space-separated string is ordered alphabetically.
        """
        sorted_non_empty_suffixes = sorted(
            suffix for suffix in pocketsuffix.values() if suffix != '')
        return " ".join(sorted_non_empty_suffixes)


class PackageRemover(SoyuzScript):
    """SoyuzScript implementation for published package removal.."""

    usage = '%prog -s warty mozilla-firefox'
    description = 'REMOVE a published package.'
    success_message = (
        "The archive will be updated in the next publishing cycle.")

    def add_my_options(self):
        """Adding local options."""
        # XXX cprov 20071025: we need a hook for loading SoyuzScript default
        # options automatically. This is ugly.
        SoyuzScript.add_my_options(self)

        # Mode options.
        self.parser.add_option("-b", "--binary", dest="binaryonly",
                               default=False, action="store_true",
                               help="Remove binaries only.")
        self.parser.add_option("-S", "--source-only", dest="sourceonly",
                               default=False, action="store_true",
                               help="Remove source only.")

        # Removal information options.
        self.parser.add_option("-u", "--user", dest="user",
                               help="Launchpad user name.")
        self.parser.add_option("-m", "--removal_comment",
                               dest="removal_comment",
                               help="Removal comment")

    def mainTask(self):
        """Execute the package removal task.

        Build location and target objects.

        Can raise SoyuzScriptError.
        """
        if len(self.args) == 0:
            raise SoyuzScriptError(
                "At least one non-option argument must be given, "
                "a package name to be removed.")

        if self.options.user is None:
            raise SoyuzScriptError("Launchpad username must be given.")

        if self.options.removal_comment is None:
            raise SoyuzScriptError("Removal comment must be given.")

        removed_by = getUtility(IPersonSet).getByName(self.options.user)
        if removed_by is None:
            raise SoyuzScriptError(
                "Invalid launchpad usename: %s" % self.options.user)

        removables = []
        for packagename in self.args:
            if self.options.binaryonly:
                removables.extend(
                    self.findLatestPublishedBinaries(packagename))
            elif self.options.sourceonly:
                removables.append(self.findLatestPublishedSource(packagename))
            else:
                source_pub = self.findLatestPublishedSource(packagename)
                removables.append(source_pub)
                removables.extend(source_pub.getPublishedBinaries())

        self.logger.info("Removing candidates:")
        for removable in removables:
            self.logger.info('\t%s' % removable.displayname)

        self.logger.info("Removed-by: %s" % removed_by.displayname)
        self.logger.info("Comment: %s" % self.options.removal_comment)

        removals = []
        for removable in removables:
            removable.requestDeletion(
                removed_by=removed_by,
                removal_comment=self.options.removal_comment)
            removals.append(removable)

        if len(removals) == 1:
            self.logger.info(
                "%s package successfully removed." % len(removals))
        elif len(removals) > 1:
            self.logger.info(
                "%s packages successfully removed." % len(removals))
        else:
            self.logger.info("No package removed (bug ?!?).")

        # Information returned mainly for the benefit of the test harness.
        return removals


class ObsoleteDistroseries(SoyuzScript):
    """`SoyuzScript` that obsoletes a distroseries."""

    usage = "%prog -d <distribution> -s <suite>"
    description = ("Make obsolete (schedule for removal) packages in an "
                  "obsolete distroseries.")

    def add_my_options(self):
        """Add -d, -s, dry-run and confirmation options."""
        SoyuzScript.add_distro_options(self)
        SoyuzScript.add_transaction_options(self)

    def mainTask(self):
        """Execute package obsolescence procedure.

        Modules using this class outside of its normal usage in the
        main script can call this method to start the copy.

        In this case the caller can override test_args on __init__
        to set the command line arguments.

        :raise SoyuzScriptError: If the distroseries is not provided or
            it is already obsolete.
        """
        assert self.location, (
            "location is not available, call SoyuzScript.setupLocation() "
            "before calling mainTask().")

        # Shortcut variable name to reduce long lines.
        distroseries = self.location.distroseries

        self._checkParameters(distroseries)

        self.logger.info("Obsoleting all packages for distroseries %s in "
                         "the %s distribution." % (
                            distroseries.name,
                            distroseries.distribution.name))

        sources = distroseries.getAllPublishedSources()
        binaries = distroseries.getAllPublishedBinaries()
        num_sources = sources.count()
        num_binaries = binaries.count()
        self.logger.info("There are %d sources and %d binaries." % (
            num_sources, num_binaries))

        if num_sources == 0 and num_binaries == 0:
            raise SoyuzScriptError("Nothing to do, no published packages.")

        self.logger.info("Obsoleting sources...")
        for package in sources:
            self.logger.debug("Obsoleting %s" % package.displayname)
            package.requestObsolescence()

        self.logger.info("Obsoleting binaries...")
        for package in binaries:
            self.logger.debug("Obsoleting %s" % package.displayname)
            package.requestObsolescence()

        # The obsoleted packages will be caught by death row processing
        # the next time it runs.  We skip the domination phase in the
        # publisher because it won't consider stable distroseries.

    def _checkParameters(self, distroseries):
        """Sanity check the supplied script parameters."""
        # Did the user provide a suite name? (distribution defaults
        # to 'ubuntu' which is fine.)
        if distroseries == distroseries.distribution.currentseries:
            # SoyuzScript defaults to the latest series.  Since this
            # will never get obsoleted it's safe to assume that the
            # user let this option default, so complain and exit.
            raise SoyuzScriptError(
                "Please specify a valid distroseries name with -s/--suite "
                "and which is not the most recent distroseries.")

        # Is the distroseries in an obsolete state?  Bail out now if not.
        if distroseries.status != SeriesStatus.OBSOLETE:
            raise SoyuzScriptError(
                "%s is not at status OBSOLETE." % distroseries.name)


class ManageChrootScript(SoyuzScript):
    """`SoyuzScript` that manages chroot files."""

    usage = "%prog -d <distribution> -s <suite> -a <architecture> -f file"
    description = "Manage the chroot files used by the builders."
    success_message = "Success."

    def add_my_options(self):
        """Add script options."""
        SoyuzScript.add_distro_options(self)
        SoyuzScript.add_transaction_options(self)
        self.parser.add_option(
            '-a', '--architecture', dest='architecture', default=None,
            help='Architecture tag')
        self.parser.add_option(
            '-f', '--filepath', dest='filepath', default=None,
            help='Chroot file path')

    def mainTask(self):
        """Set up a ChrootManager object and invoke it."""
        if len(self.args) != 1:
            raise SoyuzScriptError(
                "manage-chroot.py <add|update|remove|get>")

        [action] = self.args

        distribution = self.location.distribution
        series = self.location.distroseries

        try:
            distroarchseries = series[self.options.architecture]
        except NotFoundError, info:
            raise SoyuzScriptError("Architecture not found: %s" % info)

        # We don't want to have to force the user to confirm transactions
        # for manage-chroot.py, so disable that feature of SoyuzScript.
        self.options.confirm_all = True

        self.logger.debug(
            "Initializing ChrootManager for '%s'" % (distroarchseries.title))
        chroot_manager = ChrootManager(
            distroarchseries, filepath=self.options.filepath)

        if action in chroot_manager.allowed_actions:
            chroot_action = getattr(chroot_manager, action)
        else:
            self.logger.error(
                "Allowed actions: %s" % chroot_manager.allowed_actions)
            raise SoyuzScriptError("Unknown action: %s" % action)

        try:
            chroot_action()
        except ChrootManagerError, info:
            raise SoyuzScriptError(info)
        else:
            # Collect extra debug messages from chroot_manager.
            for debug_message in chroot_manager._messages:
                self.logger.debug(debug_message)


def generate_changes(dsc, dsc_files, suite, changelog, urgency, closes,
                     lp_closes, section, priority, description,
                     files_from_librarian, requested_by, origin):
    """Generate a Changes object.

    :param dsc: A `Dsc` instance for the related source package.
    :param suite: Distribution name
    :param changelog: Relevant changelog data
    :param urgency: Urgency string (low, medium, high, etc)
    :param closes: Sequence of Debian bug numbers (as strings) fixed by
        this upload.
    :param section: Debian section
    :param priority: Package priority
    """

    # XXX cprov 2007-07-03:
    # Changed-By can be extracted from most-recent changelog footer,
    # but do we care?

    changes = Changes()
    changes["Origin"] = "%s/%s" % (origin["name"], origin["suite"])
    changes["Format"] = "1.7"
    changes["Date"] = time.strftime("%a,  %d %b %Y %H:%M:%S %z")
    changes["Source"] = dsc["source"]
    changes["Binary"] = dsc["binary"]
    changes["Architecture"] = "source"
    changes["Version"] = dsc["version"]
    changes["Distribution"] = suite
    changes["Urgency"] = urgency
    changes["Maintainer"] = dsc["maintainer"]
    changes["Changed-By"] = requested_by
    if description:
        changes["Description"] = "\n %s" % description
    if closes:
        changes["Closes"] = " ".join(closes)
    if lp_closes:
        changes["Launchpad-bugs-fixed"] = " ".join(lp_closes)
    files = []
    for filename in dsc_files:
        if filename in files_from_librarian:
            continue
        files.append({"md5sum": dsc_files[filename]["md5sum"],
                      "size": dsc_files[filename]["size"],
                      "section": section,
                      "priority": priority,
                      "name": filename,
                     })

    changes["Files"] = files
    changes["Changes"] = "\n%s" % changelog
    return changes
