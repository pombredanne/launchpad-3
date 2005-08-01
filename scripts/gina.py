#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Gina Class.

Main gina class. handle the options and make the proper calls to the
other classes and instances.
"""

import _pythonpath

import os, sys
from string import split
from optparse import OptionParser

from canonical.launchpad.scripts.gina.database import Katie
from canonical.launchpad.scripts.gina.archive import (ArchiveComponentItems,
                                                      PackagesMap)

from canonical.launchpad.scripts.gina.handlers import ImporterHandler
from canonical.launchpad.scripts.gina.packages import (SourcePackageData,
                                                       BinaryPackageData,
                                                       MissingRequiredArguments
                                                       )

from canonical.lp.dbschema import PackagePublishingPocket
from canonical.config import config
from canonical.launchpad.scripts import logger_options, logger, log
from canonical.launchpad.scripts.lockfile import LockFile

def main(options, target_section):
    package_root = target_section.root
    keyrings_root = target_section.keyrings
    distro = target_section.distro
    distrorelease = target_section.distrorelease
    components = target_section.components.split(",")
    archs = target_section.architectures.split(",")
    pocket = target_section.pocket
    pocket_distrorelease = target_section.pocketrelease
    source_only = target_section.source_only
    spnames_only = target_section.sourcepackagenames_only

    dry_run = options.dry_run

    LPDB = config.dbname
    LPDB_HOST = config.dbhost
    LPDB_USER = config.gina.dbuser
    KTDB = target_section.katie_dbname

    if hasattr(PackagePublishingPocket, pocket.upper()):
        pocket = getattr(PackagePublishingPocket, pocket.upper())
    else:
        log.error(
            "Could not find a pocket schema for %s" % pocket
            )
        sys.exit(1)

    if not pocket_distrorelease:
        pocket_distrorelease = distrorelease

    LIBRHOST = config.librarian.upload_host
    LIBRPORT = config.librarian.upload_port
        
    log.debug("Packages read from: %s" % package_root)
    log.debug("Keyrings read from: %s" % keyrings_root)
    log.info("Archive to read: %s/%s" % (distro,distrorelease))
    log.info("Destine DistroRelease/Pocket: %s/%s" % (
        pocket_distrorelease, pocket.title.lower()
        ))
    log.info("Components to import: %s" % ", ".join(components))
    log.info("Architectures to import: %s" % ", ".join(archs))
    log.debug("Launchpad database: %s" % LPDB)
    log.debug("Launchpad database host: %s" % LPDB_HOST)
    log.debug("Launchpad database user: %s" % LPDB_USER)
    log.info("Katie database: %s" % KTDB)
    log.info("SourcePackage Only: %s" %source_only)
    log.info("SourcePackageName Only: %s" %spnames_only)
    log.debug("Librarian: %s:%s" % (LIBRHOST,LIBRPORT))
    log.info("Dry run: %s" % (dry_run))
    
    kdb = None
    if KTDB:
        kdb = Katie(KTDB, distrorelease, dry_run)

    keyrings = _get_keyring(keyrings_root)
        
    # Create the ArchComponent Items object
    arch_component_items = ArchiveComponentItems(package_root,
                                                 distrorelease,
                                                 components, archs)

    # Get the maps
    packages_map = PackagesMap(arch_component_items)

    # Create the ImporterHandler Object
    importer_handler = ImporterHandler(distro, pocket_distrorelease,
                                       dry_run)
    

    import_sourcepackages(packages_map, kdb, package_root,
                          keyrings, importer_handler, spnames_only)

    if not spnames_only:
        importer_handler.publish_sourcepackages(pocket)

    importer_handler.commit()

    if source_only:
        log.info('Source only mode... Done')
        sys.exit(0)

    if spnames_only:
        log.info('SoucePackageNames only mode... Done')
        sys.exit(0)

    import_binarypackages(pocket, packages_map, kdb, package_root,
                          keyrings, importer_handler)


def _get_keyring(keyrings_root):
    keyrings = ""
    for keyring in os.listdir(keyrings_root):
        path = os.path.join(keyrings_root, keyring)
        keyrings += " --keyring=%s" % path
    if not keyrings:
        raise AttributeError, "Keyrings not found in ./keyrings/"
    return keyrings


def import_sourcepackages(packages_map, kdb, package_root,
                          keyrings, importer_handler, spnames_only):
    """SourcePackages Import"""

    # Goes over src_map importing the sourcepackages packages.
    count = 0
    npacks = len(packages_map.src_map)
    log.info('%i SourcePackages to be imported' % npacks)
    
    for source in packages_map.src_map.itervalues():

        # If spnames flag is true, do it as fast as you can.
        if spnames_only:
            log.info('Ensuring %s name' % source['Package'])
            importer_handler.import_sourcepackagename(source['Package'])
            continue

        try:
            source_data = SourcePackageData(kdb, **source)
        except MissingRequiredArguments:
            # Required attributes for this instance was not found.
            log.exception( ("Unable to create SourcePackageData. "
                            "Required attributs not found.") )
        except (AttributeError,KeyError,ValueError,TypeError):
            # XXX: Debonzi 20050720
            # Catch all common exception since they are not predictable ATM.
            # SourcePackageData class should be refactored or rewrited to try
            # to make it better and have tested include.
            log.exception("Unable to create SourcePackageData")
            continue

        log.debug('Check Sourcepackage %s Version %s before process it' % (
            source_data.package, source_data.version
            ))

        if importer_handler.preimport_sourcecheck(source_data):
            log.debug('%s already exists' % source_data.package)
        else:
            if not source_data.process_package(kdb, package_root,
                                       keyrings):
                # Problems with katie db stuff of opening files
                log.error('Failed to import %s' % source_data.package)
                npacks -= 1
                continue

            importer_handler.import_sourcepackage(source_data)
        count += 1
        npacks -= 1
        if options.countdown > 0 and count > options.countdown:
            count = 0
            log.warn('Countdown %i sourcepackages' % npacks)
            importer_handler.commit()


def import_binarypackages(pocket, packages_map, kdb, package_root,
                          keyrings, importer_handler):
    """Binaries Import"""

    nosource = 0
    messages = []
    count = 0

    # Runs over all the architectures we have
    for arch in packages_map.bin_map.keys():
        countdown = len(packages_map.bin_map[arch])
        log.info('%i Binarypackage to be imported for %s' % (
            countdown, arch
            ))
        # Goes over the binarypackages map importing them
        # for this architecture.
        for binary in packages_map.bin_map[arch].itervalues():
            try:
                binary_data = BinaryPackageData(**binary)
            except MissingRequiredArguments:
                # Required attributes for this instance was not found.
                log.exception( ("Unable to create BinaryPackageData. "
                                "Required attributs not found.") )
            except (AttributeError, ValueError, KeyError, TypeError):
                # XXX: Debonzi 20050720
                # Catch all common exception since they are not predictable
                # ATM. BinaryPackageData class should be refactored or
                # rewrited to try to make it better and have tests included.
                log.exception("Failed to create BinaryPackageData")
                continue

            if not binary_data.process_package(kdb, package_root,
                                               keyrings):
                # Problems with katie db stuff of opening files
                log.error('Failed to import %s' % binary_data.package)
                countdown -= 1
                continue

            count += 1
            log.debug('Checking %s' % binary_data.package)
            try:
                if not importer_handler.import_binarypackage(arch, binary_data):
                    msg = 'Sourcepackage %s (%s) not found for %s (%s)' % (
                            binary_data.source, binary_data.source_version,
                            binary_data.package, binary_data.version,
                            )

                    log.warn(msg)
                    messages.append(msg)
                    nosource += 1
            except (AttributeError, ValueError, TypeError):
                log.exception("Failed to import_binarypackage")

            if options.countdown > 0 and count >= options.countdown:
                count = 0
                log.warn('Countdown %i binary packages' % countdown)
                importer_handler.commit()
            countdown -= 1
        if nosource:
            log.warn('%i Sources Not Found' % nosource)
            for pkg in messages:
                log.warn(pkg)
        importer_handler.commit()
    importer_handler.publish_binarypackages(pocket)
    importer_handler.commit()


if __name__ == "__main__":
    parser = OptionParser("Usage: %prog [OPTIONS] [target ...]")
    logger_options(parser)

    parser.add_option("-n", "--dry-run", action="store_true",
            help="Don't commit changes to the database",
            dest="dry_run", default=False)

    parser.add_option("-a", "--all", action="store_true",
            help="Run all sections defined in launchpad.conf (in order)",
            dest="all", default=False)

    parser.add_option("-c", "--countdown", action="store", type="int",
            default=0, dest="countdown", metavar="COUNT",
            help="Log a status message (as WARNING) every COUNT imports",
            )

    (options, targets) = parser.parse_args()

    possible_targets = [
        target.getSectionName() for target in config.gina.target
        ]

    if options.all:
        targets = possible_targets[:]
    else:
        if not targets:
            parser.error("Must specify at least one target to run, or --all")

        for target in targets:
            if target not in possible_targets:
                parser.error("No Gina target %s in config file" % target)

    for target in targets:
        target_section = [
            section for section in config.gina.target
                if section.getSectionName() == target][0]
        lockfile = LockFile('/var/lock/gina-%s.lock' % target)
        try:
            lockfile.acquire()
        except OSError:
            log.error(
                    'Gina already running with section %s. Skipping.' % target
                    )
        else:
            try:
                main(options, target_section)
            finally:
                lockfile.release()

