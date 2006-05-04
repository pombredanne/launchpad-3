"""Copyright Canonical Limited 2005-2004

Author: Celso Providelo <celso.providelo@canonical.com>
FTPMaster utilities.
"""
__metaclass__ = type

__all__ = [
    'ArchiveOverrider',
    'ArchiveOverriderError',
    ]

from zope.component import getUtility

from canonical.launchpad.database import (
    DistroArchReleaseBinaryPackage, DistroReleaseSourcePackageRelease)
from canonical.launchpad.interfaces import (
    IBinaryPackageNameSet, IDistributionSet, NotFoundError)
from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingPriority)


class ArchiveOverriderError(Exception):
    """ArchiveOverrider specific exception.

    Mostly used to describe errors in the initialisation of this object.
    """


class ArchiveOverrider:
    """Perform overrides on published packages.

    Used self.initialize() method to validate passed parameters.
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
