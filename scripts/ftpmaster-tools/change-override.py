#!/usr/bin/env python

"""Change the component of a package.

This tool allows you to change the component of a package.  Changes won't
take affect till the next publishing run.
"""
__metaclass__ = type

import _pythonpath

import optparse
import sys

from zope.component import getUtility
from contrib.glock import GlobalLock

from canonical.launchpad.database import (
    DistroArchReleaseBinaryPackage, DistroReleaseSourcePackageRelease)
from canonical.launchpad.interfaces import (
    IBinaryPackageNameSet, IDistributionSet, NotFoundError)
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.lp import initZopeless
from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingPriority)


class ArchiveOverriderError(Exception):
    """ArchiveOverrider specific exception.

    Mostly used to describe errors in the initialization of this object.
    """


class ArchiveOverrider:
    """Perform actions on published packages."""
    distro = None
    distrorelease = None
    pocket = None
    component = None
    section = None
    priority = None

    def __init__(self, log, distro_name=None, suite=None, component_name=None,
                 section_name=None, priority_name=None):
        """ """
        self.distro_name = distro_name
        self.suite = suite
        self.component_name = component_name
        self.section_name = section_name
        self.priority_name = priority_name
        self.log = log

    def initialize(self):
        """Initialize and validate current attributes.

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
        drspr.changeOverride(new_component=self.component,
                             new_section=self.section)
        current = drspr.current_published
        self.log.info("'%s/%s/%s' source overriden"
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
                darbp = DistroArchReleaseBinaryPackage(
                    distroarchrelease, binarypackagename)
                darbp.changeOverride(new_component=self.component,
                                     new_priority=self.priority,
                                     new_section=self.section)
            except NotFoundError:
                self.log.info("'%s' binary isn't published in %s"
                               % (package_name,
                                  distroarchrelease.architecturetag))
            else:
                current = darbp.current_published
                self.log.info(
                    "'%s/%s/%s/%s' binary overriden in %s"
                    % (package_name, current.component.name,
                       current.section.name, current.priority.name,
                       distroarchrelease.architecturetag))


def main():
    parser = optparse.OptionParser()

    logger_options(parser)

    # transaction options
    parser.add_option("-N", "--dry-run", dest="dry_run", default=False,
                      action="store_true", help="don't actually do anything")
    # muttable fields
    parser.add_option("-d", "--distro", dest="distro_name", default='ubuntu',
                      help="move package in DISTRO")
    parser.add_option("-s", "--suite", dest="suite",
                      help="move package in suite SUITE")
    parser.add_option("-c", "--component", dest="component_name",
                      help="move package to COMPONENT")
    parser.add_option("-p", "--priority", dest="priority_name",
                      help="move package to PRIORITY")
    parser.add_option("-x", "--section", dest="section_name",
                      help="move package to SECTION")
    # control options
    parser.add_option("-S", "--source-and-binary", dest="sourceandchildren",
                      default=False, action="store_true",
                      help="select source and binaries with the same name")
    parser.add_option("-B", "--binary-and-source", dest="binaryandsource",
                      default=False, action="store_true",
                      help="select source and binary (of the same name)")
    parser.add_option("-t", "--source-only", dest="sourceonly",
                      default=False, action="store_true",
                      help="select source packages only")

    (options, args) = parser.parse_args()

    log = logger(options, "change-override")

    if len(args) < 1:
        log.error("Need to be given the name of a package to move.")
        return 1

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/launchpad-change-component.lock')
    lock.acquire(blocking=True)

    log.debug("Initialising connection.")
    # XXX cprov 20060417: retrieve dbuser from config file
    ztm = initZopeless(dbuser="lucille")
    execute_zcml_for_scripts()

    # instatiate and initialize changer object
    changer = ArchiveOverrider(log, distro_name=options.distro_name,
                               suite=options.suite,
                               component_name=options.component_name,
                               section_name=options.section_name,
                               priority_name=options.priority_name)

    try:
        changer.initialize()
    except ArchiveOverriderError, info:
        log.error(info)
        return 1

    for package_name in args:
        # change matching source
        if (options.sourceonly or options.binaryandsource or
            options.sourceandchildren):
            changer.processSourceChange(package_name)

        # change all binaries for matching source
        if options.sourceandchildren:
            sp = changer.distrorelease.getSourcePackage(package_name)
            binaries = sp.currentrelease.sourcepackagerelease.binaries
            for binary_name in [binary.name for binary in binaries]:
                changer.processBinaryChange(binary_name)

        # change only binary matching name
        elif not options.sourceonly:
            changer.processBinaryChange(package_name)

    if options.dry_run:
        log.info("Dry run, aborting transaction")
        ztm.abort()
    else:
        log.info("Commiting transaction, changes will be visible after "
                 "next publisher run.")
        ztm.commit()

    lock.release()
    return 0


if __name__ == '__main__':
    sys.exit(main())
