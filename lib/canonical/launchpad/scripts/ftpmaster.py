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

from canonical.launchpad.database import (
    DistroArchReleaseBinaryPackage, DistroReleaseSourcePackageRelease)
from canonical.launchpad.interfaces import (
    IBinaryPackageNameSet, IDistributionSet, IBinaryPackageReleaseSet,
    NotFoundError)
from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingPriority)


# XXX cprov 20060502: backporting code from dak, we do not expose it via
# imports of this module.

re_extract_src_version = re.compile(r"(\S+)\s*\((.*)\)")

def secureTempFilename(directory=None, dotprefix=None, perms=0700):
    """Return a secure and unique filename by pre-creating it.
    If 'directory' is non-null, it will be the directory the file
    is pre-created in.
    If 'dotprefix' is non-null, the filename will be prefixed with a '.'.
    """
    if directory:
        old_tempdir = tempfile.tempdir;
        tempfile.tempdir = directory;

    filename = tempfile.mktemp();

    if dotprefix:
        filename = "%s/.%s" % (os.path.dirname(filename),
                               os.path.basename(filename));
    fd = os.open(filename, os.O_RDWR|os.O_CREAT|os.O_EXCL, perms);
    os.close(fd);

    if directory:
        tempfile.tempdir = old_tempdir;

    return filename;


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
        drspr = DistroReleaseSourcePackageRelease(self.distrorelease, spr)
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

            darbp = DistroArchReleaseBinaryPackage(
                distroarchrelease, binarypackagename)

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

        binaries = sp.currentrelease.sourcepackagerelease.binaries
        for binary_name in [binary.name for binary in binaries]:
            self.processBinaryChange(binary_name)


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
    source_versions = {}
    source_binaries = {}
    nbs = {}
    asba = {}
    bin_pkgs = {}
    arch_any = {}
    dubious_nbs = {}
    real_nbs = {}
    nbs_to_remove = []

    def __init__(self, logger, distribution_name='ubuntu', suite=None,
                 archive_path='/srv/launchpad.net/ubuntu-archive'):
        """ """
        self.distribution_name = distribution_name
        self.suite = suite
        self.archive_path = archive_path
        self.logger = logger

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

    def gunzipedContent(self, filename):
        """ """
        # apt_pkg.ParseTagFile needs a real file handle and
        # can't handle a GzipFile instance...
        temp_filename = secureTempFilename()
        (result, output) = commands.getstatusoutput(
            "gunzip -c %s > %s" % (filename, temp_filename))
        if (result != 0):
            raise ArchiveCruftCheckerError(
                "Gunzip invocation failed!\n%s\n" % (output))
        return temp_filename

    def buildSources(self):
        """ """
        self.logger.debug("Considering Sources:")
        for component in self.components:
            filename = os.path.join(
                self.dist_archive, "%s/source/Sources.gz" % component)

            self.logger.debug("Processing %s" % filename)
            sources_filename = self.gunzipedContent(filename)
            sources = open(sources_filename)

            Sources = apt_pkg.ParseTagFile(sources)

            while Sources.Step():
                source = Sources.Section.Find("Package")
                source_version = Sources.Section.Find("Version")
                architecture = Sources.Section.Find("Architecture")
                binaries = Sources.Section.Find("Binary")
                for binary in [item.strip() for item in binaries.split(',')]:
                    self.bin_pkgs.setdefault(binary, [])
                    self.bin_pkgs[binary].append(source)

                self.source_binaries[source] = binaries
                self.source_versions[source] = source_version

            sources.close()
            os.unlink(sources_filename)

    def buildNBS(self):
        """ """
        # Checks based on the Packages files
        self.logger.debug("Finding NBS:")
        for component in self.components_and_di:
            for architecture in self.architectures:
                self.buildArchNBS(self, component, architecture)


    def buildArchNBS(self, component, architecture):
        """ """
        # XXX de-hardcode me harder
        filename = os.path.join(
            self.dist_archive,
            "%s/binary-%s/Packages.gz" % (component, architecture))

        self.logger.debug("Processing %s" % filename)
        packages_filename = self.gunzipedContent(filename)
        packages = open(packages_filename)

        Packages = apt_pkg.ParseTagFile(packages)

        while Packages.Step():
            package = Packages.Section.Find('Package')
            source = Packages.Section.Find('Source', "")
            version = Packages.Section.Find('Version')
            architecture = Packages.Section.Find('Architecture')

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

            if apt_pkg.VersionCompare(version, self.arch_any[package]) < 1:
                self.arch_any[package] = version

        packages.close()
        os.unlink(packages_filename)

    def buildASBA(self):
        """ """
        self.logger.debug("Finding ASBA:")
        for component in self.components_and_di:
            for architecture in self.architectures:
                self.buildArchASBA(component, architecture)


    def buildArchASBA(self, component, architecture):
        """ """
        filename = os.path.join(
            self.dist_archive,
            "%s/binary-%s/Packages.gz" % (component, architecture))

        packages_filename = self.gunzipedContent(filename)
        packages = open(packages_filename)

        Packages = apt_pkg.ParseTagFile(packages)

        while Packages.Step():
            package = Packages.Section.Find('Package')
            source = Packages.Section.Find('Source', "")
            version = Packages.Section.Find('Version')
            architecture = Packages.Section.Find('Architecture')

            if source == "":
                source = package

            if source.find("(") != -1:
                m = re_extract_src_version.match(source)
                source = m.group(1)
                version = m.group(2)

            if architecture == "all":
                if (self.arch_any.has_key(package) and
                    apt_pkg.VersionCompare(version,
                                           self.arch_any[package]) > -1):
                    self.asba.setdefault(source,{})
                    self.asba[source].setdefault(package, {})
                    self.asba[source][package].setdefault(version, {})
                    self.asba[source][package][version][architecture] = ""

        packages.close()
        os.unlink(packages_filename)

    def addNBS(self, nbs_d, source, version, package):
        """ """
        # Ensure the package is still in the suite (someone may have
        # already removed it).
        bpr = getUtility(IBinaryPackageReleaseSet)
        result = bpr.getByNameInDistroRelease(
            self.distrorelease.id, package)

        if len(list(result)) == 0:
            return

        nbs_d.setdefault(source, {})
        nbs_d[source].setdefault(version, {})
        nbs_d[source][version][package] = ""

    def refineNBS(self):
        # Distinguish dubious (version numbers match) and 'real'
        # NBS (they don't)
        for source in self.nbs.keys():
            for package in self.nbs[source].keys():
                versions = self.nbs[source][package].keys()
                versions.sort(apt_pkg.VersionCompare)
                latest_version = versions.pop()

                source_version = self.source_versions.get(source, "0")

                if apt_pkg.VersionCompare(latest_version, source_version) == 0:
                    self.addNBS(self.dubious_nbs, source, latest_version,
                                package)
                else:
                    self.addNBS(self.real_nbs, source, latest_version, package)

    def outputNBS(self):
        """ """
        output = "Not Built from Source\n"
        output += "---------------------\n\n"

        nbs_keys = self.real_nbs.keys()
        nbs_keys.sort()

        for source in nbs_keys:
            output += (" * %s_%s builds: %s\n"
                       % (source, self.source_versions.get(source, "??"),
                          self.source_binaries.get(source,
                                                   "(source does not exist)")))
            output += "      but no longer builds:\n"
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
        """ """
        try:
            self.distro = getUtility(IDistributionSet)[self.distribution_name]
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
        self.buildSources()
        self.buildNBS()
        self.buildASBA()
        self.refineNBS()
        self.outputNBS()

    def doRemovals(self):
        """ """
        for package in self.nbs_to_remove:

            for distroarchrelease in self.distrorelease.architectures:
                binarypackagename = getUtility(IBinaryPackageNameSet)[package]
                darbp = DistroArchReleaseBinaryPackage(distroarchrelease,
                                                       binarypackagename)
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
