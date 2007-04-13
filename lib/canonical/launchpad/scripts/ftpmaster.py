"""Copyright Canonical Limited 2005-2004

Author: Celso Providelo <celso.providelo@canonical.com>
FTPMaster utilities.
"""
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
    'PackageLocationError',
    'PackageLocation',
    'PackageCopyError',
    'CopyPackageHelper',
    ]

import apt_pkg
import commands
import md5
import os
import re
import stat
import sys
import tempfile

from zope.component import getUtility

from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces import (
    IBinaryPackageNameSet, IDistributionSet, IBinaryPackageReleaseSet,
    ILaunchpadCelebrities, NotFoundError, ILibraryFileAliasSet)
from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingPriority)

from canonical.librarian.interfaces import (
    ILibrarianClient, UploadFailed)
from canonical.librarian.utils import copy_and_close

# XXX cprov 20060502: Redefining same regexp code from dak_utils,
# we do not expose it via imports of this module. As soon as we
# finish the redesign/cleanup of all scripts, all those expressions
# will be defined here and dak_utils won't be necessary anymore.
re_extract_src_version = re.compile(r"(\S+)\s*\((.*)\)")


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
    distrorelease = None
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
            self.distrorelease = self.distro.currentrelease
            self.pocket = PackagePublishingPocket.RELEASE
        else:
            try:
                self.distrorelease, self.pocket = (
                    self.distro.getDistroReleaseAndPocket(self.suite))
            except NotFoundError:
                raise ArchiveOverriderError(
                    "Invalid suite: '%s'" % self.suite)

        if self.component_name:
            valid_components = dict(
                [(component.name, component)
                 for component in self.distrorelease.components])
            if self.component_name not in valid_components:
                raise ArchiveOverriderError(
                    "%s is not a valid component for %s/%s."
                    % (self.component_name, self.distro.name,
                       self.distrorelease.name))
            self.component = valid_components[self.component_name]
            self.log.info("Override Component to: '%s'" % self.component.name)

        if self.section_name:
            valid_sections = dict(
                [(section.name, section)
                 for section in self.distrorelease.sections])
            if self.section_name not in valid_sections:
                raise ArchiveOverriderError(
                    "%s is not a valid section for %s/%s."
                    % (self.section_name, self.distro.name,
                       self.distrorelease.name))
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
                       self.distrorelease.name))
            self.priority = valid_priorities[self.priority_name]
            self.log.info("Override Priority to: '%s'" % self.priority.name)

    def processSourceChange(self, package_name):
        """Perform changes in a given source package name.

        It changes only the current published release.
        """
        sp = self.distrorelease.getSourcePackage(package_name)

        if not sp or not sp.currentrelease:
            self.log.error("'%s' source isn't published in %s"
                           % (package_name, self.distrorelease.name))
            return

        sp.currentrelease.changeOverride(new_component=self.component,
                                         new_section=self.section)
        self.log.info("'%s/%s/%s' source overridden"
                      % (package_name, sp.currentrelease.component.name,
                         sp.currentrelease.section.name))

    def processBinaryChange(self, package_name):
        """Perform changes in a given binary package name

        It tries to change the binary in all architectures.
        """
        for distroarchrelease in self.distrorelease.architectures:
            try:
                binarypackagename = getUtility(IBinaryPackageNameSet)[
                    package_name]
            except NotFoundError:
                self.log.error("'%s' binary not found in %s/%s"
                               % (package_name, self.distrorelease.name,
                                  distroarchrelease.architecturetag))
                return

            darbp = distroarchrelease.getBinaryPackage(binarypackagename)

            try:
                current = darbp.current_published
            except NotFoundError:
                self.log.error("'%s' binary isn't published in %s/%s"
                               % (package_name, self.distrorelease.name,
                                  distroarchrelease.architecturetag))
            else:
                darbp.changeOverride(new_component=self.component,
                                     new_priority=self.priority,
                                     new_section=self.section)
                self.log.info(
                    "'%s/%s/%s/%s' binary overridden in %s/%s"
                    % (package_name, current.component.name,
                       current.section.name, current.priority.name,
                       self.distrorelease.name,
                       distroarchrelease.architecturetag))

    def processChildrenChange(self, package_name):
        """Perform changes on all binary packages generated by this source.

        Affects only the currently published release.
        """
        sp = self.distrorelease.getSourcePackage(package_name)
        if not sp or not sp.currentrelease:
            self.log.error("'%s' source isn't published in %s"
                           % (package_name, self.distrorelease.name))
            return

        # IDRSPR.binaries returns IBPRs which have name multiplicity.
        # The set() will contain only distinct binary names.
        binaryname_set = set([binary.name for binary in
                              sp.currentrelease.binaries])
        # self.processBinaryChange will try the binary name for all
        # known architectures.
        for binaryname in binaryname_set:
            self.processBinaryChange(binaryname)


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

    # XXX cprov 20060515: the default archive path should come
    # from the IDistrorelease.lucilleconfig. But since it's still
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
                     for a in self.distrorelease.architectures])
    @property
    def components(self):
        return dict([(c.name, c) for c in self.distrorelease.components])

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
                            'dists', self.distrorelease.name)

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
                "File does not exists:%s" % filename)
        unused_fd, temp_filename = tempfile.mkstemp()
        (result, output) = commands.getstatusoutput(
            "gunzip -c %s > %s" % (filename, temp_filename))
        if result != 0:
            raise ArchiveCruftCheckerError(
                "Gunzip invocation failed!\n%s" % output)

        temp_fd = open(temp_filename)
        # XXX cprov 20060515: maybe we need some sort of data integrity
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
        result = bpr.getByNameInDistroRelease(
            self.distrorelease.id, package)

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
            self.distrorelease = self.distro.currentrelease
            self.pocket = PackagePublishingPocket.RELEASE
        else:
            try:
                self.distrorelease, self.pocket = (
                    self.distro.getDistroReleaseAndPocket(self.suite))
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

            for distroarchrelease in self.distrorelease.architectures:
                binarypackagename = getUtility(IBinaryPackageNameSet)[package]
                darbp = distroarchrelease.getBinaryPackage(binarypackagename)
                try:
                    sbpph = darbp.supersede()
                    # We're blindly removing for all arches, if it's not there
                    # for some, that's fine ...
                except NotFoundError:
                    pass
                else:
                    version = sbpph.binarypackagerelease.version
                    self.logger.info ("Removed %s_%s from %s/%s ... "
                                      % (package, version,
                                         self.distrorelease.name,
                                         distroarchrelease.architecturetag))


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

    The 'distroarchrelease' and 'pocket' arguments are mandatory and
    'filepath' is optional.

    'filepath' is required by some allowed actions as source or destination,

    ChrootManagerError will be raised if anything wrong occurred in this
    class, things like missing parameter or infrastructure pieces not in
    place.
    """

    allowed_actions = ['add', 'update', 'remove', 'get']

    def __init__(self, distroarchrelease, pocket, filepath=None):
        self.distroarchrelease = distroarchrelease
        self.pocket = pocket
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
        pocket_chroot = self.distroarchrelease.getPocketChroot(self.pocket)
        if pocket_chroot is None:
            raise ChrootManagerError(
                'Could not find chroot for %s/%s'
                % (self.distroarchrelease.title, self.pocket.name))

        self._messages.append(
            "PocketChroot for '%s'/%s (%d) retrieved."
            % (pocket_chroot.distroarchrelease.title,
               pocket_chroot.pocket.name, pocket_chroot.id))

        return pocket_chroot

    def _update(self):
        """Base method for add and update action."""
        if self.filepath is None:
            raise ChrootManagerError('Missing local chroot file path.')
        alias = self._upload()
        return self.distroarchrelease.addOrUpdateChroot(self.pocket, alias)

    def add(self):
        """Create a new PocketChroot record.

        Raises ChrootManagerError if self.filepath isn't set.
        Update of pre-existent PocketChroot record will be automaticaly
        handled.
        It's a bind to the self.update method.
        """
        pocket_chroot = self._update()
        self._messages.append(
            "PocketChroot for '%s'/%s (%d) added."
            % (pocket_chroot.distroarchrelease.title,
               pocket_chroot.pocket.name, pocket_chroot.id))

    def update(self):
        """Update a PocketChroot record.

        Raises ChrootManagerError if filepath isn't set
        Creation of inexistent PocketChroot records will be automaticaly
        handled.
        """
        pocket_chroot = self._update()
        self._messages.append(
            "PocketChroot for '%s'/%s (%d) updated."
            % (pocket_chroot.distroarchrelease.title,
               pocket_chroot.pocket.name, pocket_chroot.id))

    def remove(self):
        """Overwrite existent PocketChroot file to none.

        Raises ChrootManagerError if the chroot record isn't found.
        """
        pocket_chroot = self._getPocketChroot()
        self.distroarchrelease.addOrUpdateChroot(self.pocket, None)
        self._messages.append(
            "PocketChroot for '%s'/%s (%d) removed."
            % (pocket_chroot.distroarchrelease.title,
               pocket_chroot.pocket.name, pocket_chroot.id))

    def get(self):
        """Download chroot file from Librarian and store"""
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
        # XXX cprov 20070110: looking for files within ubuntu only.
        # It doesn't affect the usual sync-source procedure. However
        # it needs to be revisited for derivation, we probably need
        # to pass the target distribution in order to make proper lookups.
        # See further info in bug #78683.
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


class PackageLocationError(Exception):
    """Raised when something went wrong when building PackageLocation."""


class PackageLocation:
    """Object used to model locations when copying publications.

    It groups distribution + distrorelease + pocket in a way they
    can be easily manipulated and compared.
    """
    distribution = None
    distrorelease = None
    pocket = None

    def __init__(self, distribution_name, suite_name):
        """Store given parameters.

        Build LP objects and expand suite_name into distrorelease + pocket.
        """
        try:
            self.distribution = getUtility(IDistributionSet)[distribution_name]
        except NotFoundError, err:
            raise PackageLocationError(
                "Could not find distribution %s" % err)

        if suite_name is not None:
            try:
                suite = self.distribution.getDistroReleaseAndPocket(suite_name)
            except NotFoundError, err:
                raise PackageLocationError(
                    "Could not find suite %s" % err)
            else:
                self.distrorelease, self.pocket = suite
        else:
            self.distrorelease = self.distribution.currentrelease
            self.pocket = PackagePublishingPocket.RELEASE

    def __eq__(self, other):
        if (self.distribution.id == other.distribution.id and
            self.distrorelease.id == other.distrorelease.id and
            self.pocket.value == other.pocket.value):
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return '%s/%s/%s' % (self.distribution.name, self.distrorelease.name,
                             self.pocket.name)

    def __repr__(self):
        return self.__str__()


class PackageCopyError(Exception):
    """Raised when a package copy operation failed.  The textual content
    should explain the error.
    """


class CopyPackageHelper:
    synced = False
    target_source = None
    target_binaries = []
    copied_source = None
    copied_binaries = []

    def __init__(self, sourcename, sourceversion, from_suite, to_suite,
                 from_distribution_name, to_distribution_name,
                 confirm_all, comment, include_binaries, logger):
        self.sourcename = sourcename
        self.sourceversion = sourceversion
        self.from_suite = from_suite
        self.to_suite = to_suite
        self.from_distribution_name = from_distribution_name
        self.to_distribution_name = to_distribution_name

        self.confirm_all = confirm_all
        self.comment = comment
        self.include_binaries = include_binaries
        self.logger = logger

    def _buildLocations(self):
        """Build PackageLocation for context FROM and TO.

        Result is stored in self.from_location and self.to_location.
        """
        try:
            self.from_location = PackageLocation(
                self.from_distribution_name, self.from_suite)
            self.to_location = PackageLocation(
                self.to_distribution_name, self.to_suite)
        except PackageLocationError, err:
            raise PackageCopyError(err)

        if self.from_location == self.to_location:
            raise PackageCopyError(
                "Can not sync between the same locations: '%s' to '%s'" % (
                self.from_location, self.to_location))

    def _buildSource(self):
        """Build a DistroReleaseSourcePackageRelease for the given parameters

        Result is stored in self.target_source.
        """
        sourcepackage = self.from_location.distrorelease.getSourcePackage(
            self.sourcename)

        if sourcepackage is None:
            raise PackageCopyError(
                "Could not find any version of '%s' in %s" % (
                self.sourcename, self.from_location))

        if self.sourceversion is None:
            self.target_source = sourcepackage.currentrelease
        else:
            self.target_source = sourcepackage[self.sourceversion]

        if self.target_source is None:
            raise PackageCopyError(
                "Could not find '%s/%s' in %s" % (
                self.sourcename, self.sourceversion,
                self.from_location))

    def _buildBinaries(self):
        """Build a set of DistroArchReleaseBinaryPackage for the context source.

        Asserts self.target_source is already initialised.
        Result is stored in self.target_binaries.
        """
        assert self.target_source is not None, (
            "target_source needs to be initialised first.")
        # Obtain names of all distinct binary packages names
        # produced by the target_source
        binary_name_set = set(
            [binary.name for binary in self.target_source.binaries])

        # Get the binary packages in each distroarchrelease and store them
        # in target_binaries for later.
        for binary_name in binary_name_set:
            all_archs = self.from_location.distrorelease.architectures
            for distroarchrelease in all_archs:
                darbp = distroarchrelease.getBinaryPackage(binary_name)
                # only include objects with published binaries
                try:
                    current = darbp.current_published
                except NotFoundError:
                    pass
                else:
                    self.target_binaries.append(darbp)

    def _requestFeedback(self, question='Are you sure', default_answer='yes',
                         valid_answers=['yes', 'no']):
        """Command-line helper.

        It uses raw_input to collect user feedback.

        If self.confirm_all is activated the default answer is returned,
        otherwise the user input will be requested and returned.

        If valid_answers list is specified it will loop until one of the
        options is entered.
        """
        if self.confirm_all:
            return default_answer

        answer = None
        if valid_answers:
            display_answers = '[%s]' % (', '.join(valid_answers))
            full_question = '%s ? %s ' % (question, display_answers)
            while answer not in valid_answers:
                answer = raw_input(full_question)
        else:
            full_question = '%s ? ' % question
            answer = raw_input(full_question)
        return answer

    def copySource(self):
        """Copy context source and store correspondent reference.

        Asserts self.target_source is already initialised
        Reference to the destination copy will be store in
        self.copied_source.
        """
        assert self.target_source is not None, (
            "target_source needs to be initialised first.")

        self.logger.info("Performing source copy.")

        source_copy = self.target_source.copyTo(
            distrorelease=self.to_location.distrorelease,
            pocket=self.to_location.pocket)

        # Retrieve and store the IDRSPR for the target location
        to_distrorelease = self.to_location.distrorelease
        self.copied_source = to_distrorelease.getSourcePackageRelease(
            source_copy.sourcepackagerelease)

        self.synced = True
        self.logger.info("Copied: %s" % self.copied_source.title)

    def copyBinary(self, binary):
        """Copy given binary to target location if possible.

        Store reference to the copied binary in the target location.
        """
        # copyTo will raise NotFoundError if the architecture in
        # question is not present in destination or if the binary
        # is not published it source location. Both situations are
        # safe, so that's why we swallow this error.
        try:
            binary_copy = binary.copyTo(
                distrorelease=self.to_location.distrorelease,
                pocket=self.to_location.pocket)
        except NotFoundError:
            pass
        else:
            # Retrieve and store the IDARBPR for the target location.
            darbp = binary_copy.distroarchrelease.getBinaryPackage(
                binary_copy.binarypackagerelease.name)
            bin_version = binary_copy.binarypackagerelease.version
            binary_copied = darbp[bin_version]
            self.copied_binaries.append(binary_copied)

            self.synced = True
            self.logger.info("Copied: %s" % binary_copied.title)

    def performCopy(self):
        """Execute package copy procedure.

        Build location and target objects.
        Request user feedback is not suppressed by given parameters.
        Copy source publication and optionally related binary publications
        according to the given parameters.
        """
        self._buildLocations()
        self._buildSource()

        self.logger.info("Syncing '%s' TO '%s'" % (self.target_source.title,
                                                   self.to_location))
        self.logger.info("Comment: %s" % self.comment)
        self.logger.info("Include Binaries: %s" % self.include_binaries)

        confirmation = self._requestFeedback()
        if confirmation != 'yes':
            self.logger.info("Ok, see you later")
            return

        self.copySource()

        if self.include_binaries:
            self.logger.info("Performing binary copy.")
            self._buildBinaries()
            for binary in self.target_binaries:
                self.copyBinary(binary)
            self.logger.info(
                "%d binaries copied." % len(self.copied_binaries))
