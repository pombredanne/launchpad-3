# Copyright 2007 Canonical Ltd.  All rights reserved.
"""FTPMaster utilities."""

__metaclass__ = type

__all__ = [
    'ArchiveOverrider',
    'ArchiveOverriderError',
    'ArchiveCruftChecker',
    'ArchiveCruftCheckerError',
    'PubSourceChecker',
    'ChrootManager',
    'ChrootManagerError',
    'SyncSource',
    'SyncSourceError',
    'PackageCopyError',
    'PackageCopier',
    'LpQueryDistro',
    'PackageRemover',
    ]

import apt_pkg
import commands
import md5
import os
import stat
import sys
import tempfile

from zope.component import getUtility

from canonical.archiveuploader.utils import re_extract_src_version
from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces import (
    DistroSeriesStatus, IBinaryPackageNameSet, IDistributionSet,
    IBinaryPackageReleaseSet, ILaunchpadCelebrities, NotFoundError,
    ILibraryFileAliasSet, IPersonSet, PackagePublishingPocket,
    PackagePublishingPriority)
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)
from canonical.lp import READ_COMMITTED_ISOLATION
from canonical.librarian.interfaces import (
    ILibrarianClient, UploadFailed)
from canonical.librarian.utils import copy_and_close
from canonical.launchpad.scripts.ftpmasterbase import (
    PackageLocation, PackageLocationError, SoyuzScript, SoyuzScriptError)


class ArchiveOverriderError(Exception):
    """ArchiveOverrider specific exception.

    Mostly used to describe errors in the initialisation of this object.
    """


class ArchiveOverrider:
    """Perform overrides on published packages.

    Use self.initialize() method to validate passed parameters.
    It will raise ArchiveOverriderError exception if anything goes wrong.
    """
    distro = None
    distroseries = None
    pocket = None
    component = None
    section = None
    priority = None

    def __init__(self, log, distro_name=None, suite=None, component_name=None,
                 section_name=None, priority_name=None):
        """Locally store passed attributes."""
        self.distro_name = distro_name
        self.suite = suite
        self.component_name = component_name
        self.section_name = section_name
        self.priority_name = priority_name
        self.log = log

    def initialize(self):
        """Initialises and validates current attributes.

        Raises ArchiveOverriderError if failed.
        """
        if (not self.component_name and not self.section_name and
            not self.priority_name):
            raise ArchiveOverriderError(
                "Need either a component, section or priority to change.")

        try:
            self.distro = getUtility(IDistributionSet)[self.distro_name]
        except NotFoundError:
            raise ArchiveOverriderError(
                "Invalid distribution: '%s'" % self.distro_name)

        if not self.suite:
            self.distroseries = self.distro.currentseries
            self.pocket = PackagePublishingPocket.RELEASE
        else:
            try:
                self.distroseries, self.pocket = (
                    self.distro.getDistroSeriesAndPocket(self.suite))
            except NotFoundError:
                raise ArchiveOverriderError(
                    "Invalid suite: '%s'" % self.suite)

        if self.component_name:
            valid_components = dict(
                [(component.name, component)
                 for component in self.distroseries.upload_components])
            if self.component_name not in valid_components:
                raise ArchiveOverriderError(
                    "%s is not a valid component for %s/%s."
                    % (self.component_name, self.distro.name,
                       self.distroseries.name))
            self.component = valid_components[self.component_name]
            self.log.info("Override Component to: '%s'" % self.component.name)

        if self.section_name:
            valid_sections = dict(
                [(section.name, section)
                 for section in self.distroseries.sections])
            if self.section_name not in valid_sections:
                raise ArchiveOverriderError(
                    "%s is not a valid section for %s/%s."
                    % (self.section_name, self.distro.name,
                       self.distroseries.name))
            self.section = valid_sections[self.section_name]
            self.log.info("Override Section to: '%s'" % self.section.name)

        if self.priority_name:
            valid_priorities = dict(
                [(priority.name.lower(), priority)
                 for priority in PackagePublishingPriority.items])
            if self.priority_name not in valid_priorities:
                raise ArchiveOverriderError(
                    "%s is not a valid priority for %s/%s."
                    % (self.priority_name, self.distro.name,
                       self.distroseries.name))
            self.priority = valid_priorities[self.priority_name]
            self.log.info("Override Priority to: '%s'" % self.priority.name)

    def processSourceChange(self, package_name):
        """Perform changes in a given source package name.

        It changes only the current published package release.
        """
        sp = self.distroseries.getSourcePackage(package_name)

        if not sp or not sp.currentrelease:
            self.log.error("'%s' source isn't published in %s"
                           % (package_name, self.distroseries.name))
            return

        sp.currentrelease.current_published.changeOverride(
            new_component=self.component, new_section=self.section)
        self.log.info("'%s/%s/%s' source overridden"
                      % (package_name, sp.currentrelease.component.name,
                         sp.currentrelease.section.name))

    def processBinaryChange(self, package_name):
        """Perform changes in a given binary package name

        It tries to change the current binary publication in all architectures.
        """
        # Check if the name is known.
        try:
            binarypackagename = getUtility(IBinaryPackageNameSet)[
                package_name]
        except NotFoundError:
            self.log.error("'%s' binary not found." % package_name)
            return

        for distroarchseries in self.distroseries.architectures:
            self._performBinaryOverride(distroarchseries, package_name)

    def processChildrenChange(self, package_name):
        """Perform changes on all binary packages generated by this source.

        Affects only the currently published release where the binary is
        directly related to the source version.
        """
        sp = self.distroseries.getSourcePackage(package_name)
        if not sp or not sp.currentrelease:
            self.log.error("'%s' source isn't published in %s"
                           % (package_name, self.distroseries.name))
            return
        if sp.currentrelease.binaries.count() == 0:
            self.log.warn("'%s' has no binaries published in %s"
                          % (package_name, self.distroseries.name))
            return

        # Process all binaries related to the current source package release.
        for bpr in sp.currentrelease.binaries:
            # Inspect binary architecturespecific flag and avoid unnecessary
            # iterations (on distroarchseries that obviously do not contain
            # any publication).
            if bpr.architecturespecific:
                considered_archs = [bpr.build.distroarchseries]
            else:
                considered_archs = self.distroseries.architectures
            # Perform overrides.
            for distroarchseries in considered_archs:
                self._performBinaryOverride(distroarchseries, bpr.name)

    def _performBinaryOverride(self, distroarchseries, binaryname):
        """Override the published binary version in the given context.

        Receive a binary name and a distroarchseries, warns and return if
        no published version could be found.
        """
        dasbp = distroarchseries.getBinaryPackage(binaryname)
        try:
            current = dasbp.current_published
        except NotFoundError:
            self.log.warn("'%s' binary isn't published in %s/%s"
                          % (binaryname, self.distroseries.name,
                             distroarchseries.architecturetag))
            return
        dasbpr = dasbp[current.binarypackagerelease.version]
        dasbpr.current_publishing_record.changeOverride(
            new_component=self.component,
            new_priority=self.priority,
            new_section=self.section)
        self.log.info(
            "'%s/%s/%s/%s' binary overridden in %s/%s"
            % (binaryname, current.component.name,
               current.section.name, current.priority.name,
               self.distroseries.name,
               distroarchseries.architecturetag))


class ArchiveCruftCheckerError(Exception):
    """ArchiveCruftChecker specific exception.

    Mostly used to describe errors in the initialisation of this object.
    """

class ArchiveCruftChecker:
    """Perform overall checks to identify and remove obsolete records.

    Use initialize() method to validate passed parameters and build the
    infrastructure variables. It will raise ArchiveCruftCheckerError if
    something goes wrong.
    """

    # XXX cprov 2006-05-15: the default archive path should come
    # from the IDistroSeries.lucilleconfig. But since it's still
    # not optimal and we have real plans to migrate it from DB
    # text field to default XML config or a more suitable/reliable
    # method it's better to not add more obsolete code to handle it.
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
        return os.path.join(self.archive_path, self.distro.name,
                            'dists', self.distroseries.name)

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
            raise ArchiveCruftCheckerError(
                "File does not exist: %s" % filename)
        unused_fd, temp_filename = tempfile.mkstemp()
        (result, output) = commands.getstatusoutput(
            "gunzip -c %s > %s" % (filename, temp_filename))
        if result != 0:
            raise ArchiveCruftCheckerError(
                "Gunzip invocation failed!\n%s" % output)

        temp_fd = open(temp_filename)
        # XXX cprov 2006-05-15: maybe we need some sort of data integrity
        # check at this point, and maybe keep the uncrompressed file
        # for debug purposes, let's see how it behaves in real conditions.
        parsed_contents = apt_pkg.ParseTagFile(temp_fd)

        return temp_fd, temp_filename, parsed_contents

    def processSources(self):
        """Process archive sources index.

        Build source_binaries, source_versions and bin_pkgs lists.
        """
        self.logger.debug("Considering Sources:")
        for component in self.components:
            filename = os.path.join(
                self.dist_archive, "%s/source/Sources.gz" % component)

            self.logger.debug("Processing %s" % filename)
            temp_fd, temp_filename, parsed_sources = (
                self.gunzipTagFileContent(filename))
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
        temp_fd, temp_filename, parsed_packages = (
            self.gunzipTagFileContent(filename))
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

                if not self.bin_pkgs.has_key(package):
                    self.nbs.setdefault(source, {})
                    self.nbs[source].setdefault(package, {})
                    self.nbs[source][package][version] = ""

                if architecture != "all":
                    self.arch_any.setdefault(package, "0")
                    if apt_pkg.VersionCompare(
                        version,self.arch_any[package]) < 1:
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

        temp_fd, temp_filename, parsed_packages = (
            self.gunzipTagFileContent(filename))

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
                    if (self.arch_any.has_key(package) and
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
        bpr = getUtility(IBinaryPackageReleaseSet)
        result = bpr.getByNameInDistroSeries(
            self.distroseries, package)

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

                if apt_pkg.VersionCompare(latest_version, source_version) == 0:
                    self.addNBS(
                        self.dubious_nbs, source, latest_version, package)
                else:
                    self.addNBS(self.real_nbs, source, latest_version, package)

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

                output += "        o %s: %s\n" % (version, ", ".join(packages))

            output += "\n"

        if self.nbs_to_remove:
            self.logger.info(output)
        else:
            self.logger.debug("No NBS found")

    def initialize(self):
        """Initialise and build required lists of obsolete entries in archive.

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

        if not os.path.exists(self.archive_path):
            raise ArchiveCruftCheckerError(
                "Invalid archive path: '%s'" % self.archive_path)

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
                    sbpph = dasbpr.current_publishing_record.supersede()
                    # We're blindly removing for all arches, if it's not there
                    # for some, that's fine ...
                except NotFoundError:
                    pass
                else:
                    version = sbpph.binarypackagerelease.version
                    self.logger.info ("Removed %s_%s from %s/%s ... "
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

        Return None if no issue was annotated or an formatted string including:

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
            alias_id  = getUtility(ILibrarianClient).addFile(
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

    def __init__(self, files, origin, debug, downloader):
        """Store local context.

        files: a dictionary where the keys are the filename and the
               value another dictionary with the file informations.
        origin: a dictionary similar to 'files' but where the values
                contain information for download files to be synchronized
        debug: a debug function, 'debug(message)'
        downloader: a callable that fetchs URLs, 'downloader(url, destination)'
        """
        self.files = files
        self.origin = origin
        self.debug = debug
        self.downloader = downloader

    @classmethod
    def generateMD5Sum(self, filename):
        file_handle = open(filename)
        md5sum = md5.md5(file_handle.read()).hexdigest()
        file_handle.close()
        return md5sum

    def fetchFileFromLibrarian(self, filename):
        """Fetch file from librarian.

        Store the contents in local path with the original filename.
        Return the fetched filename if it was present in Librarian or None
        if it wasn't.
        """
        # XXX cprov 2007-01-10 bug=78683: Looking for files within ubuntu
        # only. It doesn't affect the usual sync-source procedure. However
        # it needs to be revisited for derivation, we probably need
        # to pass the target distribution in order to make proper lookups.
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        try:
            libraryfilealias = ubuntu.getFileByName(
                filename, source=True, binary=False)
        except NotFoundError:
            return None

        self.debug(
            "\t%s: already in distro - downloading from librarian" %
            filename)

        output_file = open(filename, 'w')
        libraryfilealias.open()
        copy_and_close(libraryfilealias, output_file)
        return filename

    def fetchLibrarianFiles(self):
        """Try to fetch files from Librarian.

        It raises SyncSourceError if anything else then an
        'orig.tar.gz' was found in Librarian.
        Return a boolean indicating whether or not the 'orig.tar.gz' is
        required in the upload.
        """
        orig_filename = None
        for filename in self.files.keys():
            if not self.fetchFileFromLibrarian(filename):
                continue
            # set the return code if an orig was, in fact,
            # fetched from Librarian
            if filename.endswith("orig.tar.gz"):
                orig_filename = filename
            else:
                raise SyncSourceError(
                    'Oops, only orig.tar.gz can be retrieved from librarian')

        return orig_filename

    def fetchSyncFiles(self):
        """Fetch files from the original sync source.

        Return DSC filename, which should always come via this path.
        """
        dsc_filename = None
        for filename in self.files.keys():
            if os.path.exists(filename):
                continue
            self.debug(
                "  - <%s: downloading from %s>" %
                (filename, self.origin["url"]))
            download_f = ("%s%s" % (self.origin["url"],
                                    self.files[filename]["remote filename"]))
            sys.stdout.flush()
            self.downloader(download_f, filename)
            # only set the dsc_filename if the DSC was really downloaded.
            # this loop usually includes the other files for the upload,
            # DIFF and ORIG.
            if filename.endswith(".dsc"):
                dsc_filename = filename

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


class PackageCopyError(Exception):
    """Raised when a package copy operation failed.  The textual content
    should explain the error.
    """


class PackageCopier(LaunchpadScript):
    """LaunchpadScript that copies published packages between distro suites.

    Possible exceptions raised are:
    * PackageLocationError: specified package or distro does not exist
    * PackageCopyError: the copy operation itself has failed
    * LaunchpadScriptError: only raised if entering via main(), ie this
        code is running as a genuine script.  In this case, this is
        also the _only_ exception to be raised.

    The test harness doesn't enter via main(), it calls doCopy(), so
    it only sees the first two exceptions.
    """

    usage = '%prog -s warty mozilla-firefox --to-suite hoary'
    description = 'MOVE or COPY a published package to another suite.'

    def add_my_options(self):

        self.parser.add_option(
            '-n', '--dry-run', dest='dryrun', default=False,
            action='store_true', help='Do not commit changes.')

        self.parser.add_option(
            '-y', '--confirm-all', dest='confirm_all',
            default=False, action='store_true',
            help='Do not prompt the user for confirmation.')

        self.parser.add_option(
            '-b', '--include-binaries', dest='include_binaries',
            default=False, action='store_true',
            help='Whether to copy related binaries or not.')

        self.parser.add_option(
            '-d', '--from-distribution', dest='from_distribution_name',
            default='ubuntu', action='store',
            help='Source distribution.')

        self.parser.add_option(
            '-s', '--from-suite', dest='from_suite', default=None,
            action='store', help='Source suite.')

        self.parser.add_option(
            '--to-suite', dest='to_suite', default=None,
            action='store', help='Destination suite.')

        self.parser.add_option(
            '-e', '--sourceversion', dest='sourceversion', default=None,
            action='store',
            help='Optional Source Version, defaults to the current version.')

    def main(self):
        """LaunchpadScript entry point.

        Can only raise LaunchpadScriptFailure - other exceptions are
        absorbed into that.
        """

        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)

        if len(self.args) != 1:
            raise LaunchpadScriptFailure(
                "At least one non-option argument must be given, "
                "the sourcename.")

        try:
            self.doCopy()
        except (PackageCopyError, PackageLocationError), err:
            raise LaunchpadScriptFailure(err)

        if not self.options.dryrun:
            self.txn.commit()
            self.logger.info(
                "Changes committed.  The archive will be updated"
                " in the next publishing cycle")
            self.logger.info('Be patient.')
        else:
            self.logger.info('Dry run, so nothing to commit.')
            self.txn.abort()

        self.logger.info('Done.')

    def doCopy(self):
        """Execute package copy procedure.

        Build location and target objects.
        Check whether user feedback is needed or is suppressed by
        given parameters.
        Copy source publication and optionally related binary publications
        according to the given parameters.

        Modules using this class outside of its normal usage in the
        copy-package.py script can call this method to start the copy.

        In this case the caller can override test_args on __init__
        to set the command line arguments.

        Can raise PackageLocationError or PackageCopyError.
        """
        sourcename = self.args[0]
        from_source = None
        from_binaries = []
        copied_source = None
        copied_binaries = []

        # This can raise PackageCopyError:
        from_location, to_location = self._findLocations()
        from_source = self._findSource(
            from_location,
            sourcename,
            self.options.sourceversion)

        self.logger.info("Syncing %r to %r" % (from_source.title,
                                               str(to_location)))
        self.logger.info("Include Binaries: %s" % self.options.include_binaries)

        if not self.options.confirm_all and not self._getUserConfirmation():
            self.logger.info("Ok, see you later")
            return

        copied_source = self.copySource(from_source, to_location)

        if self.options.include_binaries:
            self.logger.info("Performing binary copy.")
            from_binaries = self._findBinaries(from_source, from_location)
            for binary in from_binaries:
                binary_copied = self.copyBinary(binary, to_location)
                if binary_copied is not None:
                    copied_binaries.append(binary_copied)
            self.logger.info(
                "%d binaries copied." % len(copied_binaries))

        # Information returned mainly for the benefit of the test harness.
        return (from_location, to_location, from_source, from_binaries,
                copied_source, copied_binaries)

    def _findLocations(self):
        """Build PackageLocation for context FROM and TO.

        Returns result as a tuple.
        """
        # These can raise PackageLocationError, but we're happy to pass
        # it upwards.
        from_location = PackageLocation(
            self.options.from_distribution_name, self.options.from_suite)
        # from_distribution_name intentionally used here as we currently
        # only support moving within the same distro:
        to_location = PackageLocation(
            self.options.from_distribution_name, self.options.to_suite)

        if from_location == to_location:
            raise PackageCopyError(
                "Can not sync between the same locations: '%s' to '%s'" % (
                from_location, to_location))
        return (from_location, to_location)

    def _findSource(self, from_location, sourcename, sourceversion):
        """Build a DistroSeriesSourcePackageRelease for the given parameters

        Result is returned.
        """
        sourcepackage = from_location.distroseries.getSourcePackage(
            sourcename)

        if sourcepackage is None:
            raise PackageCopyError(
                "Could not find any version of '%s' in %s" % (
                sourcename, from_location))

        if sourceversion is None:
            target_source = sourcepackage.currentrelease
        else:
            target_source = sourcepackage[sourceversion]

        if target_source is None:
            raise PackageCopyError(
                "Could not find '%s/%s' in %s" % (
                sourcename, self.options.sourceversion,
                from_location))
        return target_source

    def _findBinaries(self, from_source, from_location):
        """Build a set of DistroArchSeriesBinaryPackageRelease for the source.

        Returns a list of published DistroArchSeriesBinaryPackageRelease for
        all architectures for the from_source.
        """
        target_binaries = []

        # Get the binary packages in each distroarchseries and store them
        # in target_binaries for returning.  We are looking for *published*
        # binarypackagereleases in all arches for the from_source and its
        # from_location.
        for binary in from_source.binaries:
            if binary.architecturespecific:
                considered_arches = [binary.build.distroarchseries]
            else:
                considered_arches = from_location.distroseries.architectures

            for distroarchseries in considered_arches:
                dasbpr = distroarchseries.getBinaryPackage(
                    binary.name)[binary.version]
                # Only include objects with published binaries.
                if dasbpr is None or dasbpr.current_publishing_record is None:
                    continue
                target_binaries.append(dasbpr)

        return target_binaries

    def _getUserConfirmation(self):
        """Command-line helper.

        It uses raw_input to collect user feedback.

        Return True if the user typed 'yes' or False for 'no'.
        """
        answer = None
        valid_answers = ['yes', 'no']
        display_answers = '[%s]' % (', '.join(valid_answers))
        full_question = 'Are you sure? %s ' % display_answers
        while answer not in valid_answers:
            answer = raw_input(full_question)
        return answer == 'yes'

    def copySource(self, from_source, to_location):
        """Copy context source and store correspondent reference.

        Reference to the destination copy will be returned.
        """
        self.logger.info("Performing source copy.")

        source_copy = from_source.current_published.copyTo(
            distroseries=to_location.distroseries,
            pocket=to_location.pocket)

        # Retrieve and store the IDRSPR for the target location
        to_distroseries = to_location.distroseries
        copied_source = to_distroseries.getSourcePackageRelease(
            source_copy.sourcepackagerelease)

        self.logger.info("Copied: %s" % copied_source.title)

        return copied_source

    def copyBinary(self, binary, to_location):
        """Copy given binary to target location if possible.

        Return reference to the copied binary.
        """
        # copyTo will raise NotFoundError if the architecture in
        # question is not present in destination or if the binary
        # is not published it source location. Both situations are
        # safe, so that's why we swallow this error.
        try:
            binary_copy = binary.current_publishing_record.copyTo(
                distroseries=to_location.distroseries,
                pocket=to_location.pocket)
        except NotFoundError:
            return None

        # Retrieve and store the IDARBPR for the target location.
        darbp = binary_copy.distroarchseries.getBinaryPackage(
            binary_copy.binarypackagerelease.name)
        bin_version = binary_copy.binarypackagerelease.version
        binary_copied = darbp[bin_version]

        self.logger.info("Copied: %s" % binary_copied.title)
        return binary_copied


class LpQueryDistro(LaunchpadScript):
    """Main class for scripts/ftpmaster-tools/lp-query-distro.py."""

    def __init__(self, *args, **kwargs):
        """Initialise dynamic 'usage' message and LaunchpadScript parent.

        Also initialise the list 'allowed_arguments'.
        """
        self.allowed_actions = [
            'current', 'development', 'archs', 'official_archs',
            'nominated_arch_indep']
        self.usage = '%%prog <%s>' % ' | '.join(self.allowed_actions)
        LaunchpadScript.__init__(self, *args, **kwargs)

    def add_my_options(self):
        """Add 'distribution' and 'suite' context options."""
        self.parser.add_option(
            '-d', '--distribution', dest='distribution_name',
            default='ubuntu', help='Context distribution name.')
        self.parser.add_option(
            '-s', '--suite', dest='suite_name', default=None,
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
            self.location = PackageLocation(
                distribution_name=self.options.distribution_name,
                suite_name=self.options.suite_name)
        except PackageLocationError, err:
            raise LaunchpadScriptFailure(err)

    def defaultPresenter(self, result):
        """Default result presenter.

        Directly prints result in the standard output (print).
        """
        print result

    def runAction(self, presenter=None):
        """Run a given initialised action (self.action_name).

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
            action_result = getattr(self, 'get_' + self.action_name)
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
        if self.options.suite_name is not None:
            raise LaunchpadScriptFailure(
                "Action does not accept defined suite_name.")

    # XXX cprov 2007-04-20 bug=113563.: Should be implemented in
    # IDistribution. raising NotFoundError instead.
    def getSeriesByStatus(self, status):
        """Query context distribution for a distroseries in a given status.

        I may raise LaunchpadScriptError if no suitable distroseries in a
        given status was found.
        """
        # XXX sabdfl 2007-05-27: Isn't this a bit risky, if there are
        # multiple series with the desired status?
        for series in self.location.distribution.serieses:
            if series.status == status:
                return series
        raise LaunchpadScriptFailure(
                "Could not find a %s distroseries in %s"
                % (status.name, self.location.distribution.name))

    @property
    def get_current(self):
        """Return the name of the CURRENT distroseries.

        It is restricted for the context distribution.
        It may raise LaunchpadScriptFailure if a suite was passed in the
        command-line.
        See self.getSeriesByStatus for further information
        """
        self.checkNoSuiteDefined()
        series = self.getSeriesByStatus(
            DistroSeriesStatus.CURRENT)
        return series.name

    @property
    def get_development(self):
        """Return the name of the DEVELOPMENT distroseries.

        It is restricted for the context distribution.
        It may raise LaunchpadScriptFailure if a suite was passed in the
        command-line.
        See self.getSeriesByStatus for further information
        """
        self.checkNoSuiteDefined()
        series = self.getSeriesByStatus(
            DistroSeriesStatus.DEVELOPMENT)
        return series.name

    @property
    def get_archs(self):
        """Return a space-separated list of architecture tags.

        It is restricted for the context distribution and suite.
        """
        architectures = self.location.distroseries.architectures
        return " ".join(arch.architecturetag for arch in architectures)

    @property
    def get_official_archs(self):
        """Return a space-separated list of official architecture tags.

        It is restricted to the context distribution and suite.
        """
        architectures = self.location.distroseries.architectures
        return " ".join(arch.architecturetag
                        for arch in architectures
                        if arch.official)

    @property
    def get_nominated_arch_indep(self):
        """Return the nominated arch indep architecture tag.

        It is restricted to the context distribution and suite.
        """
        series = self.location.distroseries
        return series.nominatedarchindep.architecturetag


class PackageRemover(SoyuzScript):
    """SoyuzScript implementation for published package removal.."""

    usage = '%prog -s warty mozilla-firefox'
    description = 'REMOVE a published package.'
    success_message = (
        "The archive will be updated in the next publishing cycle.")

    def addExtraSoyuzOptions(self):
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
        if len(self.args) != 1:
            raise SoyuzScriptError(
                "Exactly one non-option argument must be given, "
                "the packagename.")

        packagename = self.args[0]

        if self.options.user is None:
            raise SoyuzScriptError("Launchpad username must be given.")

        if self.options.removal_comment is None:
            raise SoyuzScriptError("Removal comment must be given.")

        removed_by = getUtility(IPersonSet).getByName(self.options.user)
        if removed_by is None:
            raise SoyuzScriptError(
                "Invalid launchpad usename: %s" % self.options.user)

        removables = []
        if self.options.binaryonly:
            binary_pubs = self.findBinaries(packagename)
            removables.extend([b for b in binary_pubs])
        elif self.options.sourceonly:
            source_pub = self.findSource(packagename)
            removables.append(source_pub)
        else:
            source_pub = self.findSource(packagename)
            binary_pubs = source_pub.publishedBinaries()
            removables.append(source_pub)
            removables.extend([b for b in binary_pubs])

        self.logger.info("Removing candidates:")
        for removable in removables:
            self.logger.info('\t%s' % removable.displayname)

        self.logger.info("Removed-by: %s" % removed_by.displayname)
        self.logger.info("Comment: %s" % self.options.removal_comment)

        removals = []
        for removable in removables:
            removed = removable.requestDeletion(
                removed_by=removed_by,
                removal_comment=self.options.removal_comment)
            removals.append(removed)

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
