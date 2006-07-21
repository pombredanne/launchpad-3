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
    ]

import commands
import os
import re
import tempfile
import apt_pkg

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IBinaryPackageNameSet, IDistributionSet, IBinaryPackageReleaseSet,
    ILaunchpadCelebrities, NotFoundError)
from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingPriority)

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
        spr = self.distrorelease.getSourcePackage(
            package_name).releasehistory[-1]
        drspr = self.distrorelease.getSourcePackageRelease(spr)
        try:
            current = drspr.current_published
        except NotFoundError, info:
            self.log.error(info)
        else:
            drspr.changeOverride(new_component=self.component,
                                 new_section=self.section)
            self.log.info("'%s/%s/%s' source overridden"
                          % (package_name, current.component.name,
                             current.section.name))

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
        if not sp.currentrelease:
            self.log.error("'%s' source isn't published in %s"
                           % (package_name, self.distrorelease.name))
            return

        for binary in sp.currentrelease.binaries:
            self.processBinaryChange(binary.name)


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
        return dict([(a.architecturetag,a)
                     for a in self.distrorelease.architectures])
    @property
    def components(self):
        return dict([(c.name,c) for c in self.distrorelease.components])

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
                    self.nbs.setdefault(source,{})
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
                        self.asba.setdefault(source,{})
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
