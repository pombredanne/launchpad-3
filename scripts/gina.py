#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""
Gina launcher script. Handles commandline options and makes the proper
calls to the other classes and instances.

The callstack is essentially:
    main -> run_gina 
                -> import_sourcepackages -> do_one_sourcepackage
                -> import_binarypackages -> do_one_binarypackage
"""

# Set to non-zero if you'd like to be warned every so often
COUNTDOWN = 0

import _pythonpath

import os
import sys
import psycopg
from optparse import OptionParser
from datetime import timedelta

from canonical.launchpad.scripts.gina.katie import Katie
from canonical.launchpad.scripts.gina.archive import (ArchiveComponentItems,
                                                      PackagesMap)

from canonical.launchpad.scripts.gina.handlers import ImporterHandler
from canonical.launchpad.scripts.gina.packages import (SourcePackageData,
    BinaryPackageData, MissingRequiredArguments, PackageFileProcessError)

from canonical.lp.dbschema import PackagePublishingPocket
from canonical.config import config
from canonical.launchpad.scripts import logger_options, log
from canonical.launchpad.scripts.lockfile import LockFile


def _get_keyring(keyrings_root):
    # XXX: untested
    keyrings = ""
    for keyring in os.listdir(keyrings_root):
        path = os.path.join(keyrings_root, keyring)
        keyrings += " --keyring=%s" % path
    if not keyrings:
        raise AttributeError("Keyrings not found in ./keyrings/")
    return keyrings


def main():
    parser = OptionParser("Usage: %prog [OPTIONS] [target ...]")
    logger_options(parser)

    parser.add_option("-n", "--dry-run", action="store_true",
            help="Don't commit changes to the database",
            dest="dry_run", default=False)

    parser.add_option("-a", "--all", action="store_true",
            help="Run all sections defined in launchpad.conf (in order)",
            dest="all", default=False)

    parser.add_option(
            "-l", "--lockfile", default="/var/lock/launchpad-gina.lock",
            help="Ensure only one process is running that locks LOCKFILE",
            metavar="LOCKFILE"
            )

    (options, targets) = parser.parse_args()

    possible_targets = [target.getSectionName() for target
                        in config.gina.target]

    if options.all:
        targets = possible_targets[:]
    else:
        if not targets:
            parser.error("Must specify at least one target to run, or --all")

        for target in targets:
            if target not in possible_targets:
                parser.error("No Gina target %s in config file" % target)

    lockfile = LockFile(options.lockfile, timeout=timedelta(days=1),
                        logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info('Lockfile %s already locked. Exiting.', options.lockfile)
        sys.exit(1)

    try:
        for target in targets:
            target_sections = [section for section in config.gina.target
                               if section.getSectionName() == target]
            # XXX: should be a proper exception -- kiko, 2005-10-18
            assert len(target_sections) == 1
            run_gina(options, target_sections[0])
    finally:
        lockfile.release()


def run_gina(options, target_section):
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
    log.info("Archive to read: %s/%s" % (distro, distrorelease))
    log.info("Destination DistroRelease/Pocket: %s/%s" % (
        pocket_distrorelease, pocket.title.lower()))
    log.info("Components to import: %s" % ", ".join(components))
    log.info("Architectures to import: %s" % ", ".join(archs))
    log.debug("Launchpad database: %s" % LPDB)
    log.debug("Launchpad database host: %s" % LPDB_HOST)
    log.debug("Launchpad database user: %s" % LPDB_USER)
    log.info("Katie database: %s" % KTDB)
    log.info("SourcePackage Only: %s" % source_only)
    log.info("SourcePackageName Only: %s" % spnames_only)
    log.debug("Librarian: %s:%s" % (LIBRHOST, LIBRPORT))
    log.info("Dry run: %s" % (dry_run))
    log.info("")

    kdb = None
    if KTDB:
        kdb = Katie(KTDB, distrorelease, dry_run)

    keyrings = _get_keyring(keyrings_root)

    # Create the ArchComponent Items object
    arch_component_items = ArchiveComponentItems(package_root,
                                                 distrorelease,
                                                 components, archs)

    packages_map = PackagesMap(arch_component_items)
    importer_handler = ImporterHandler(distro, pocket_distrorelease,
                                       dry_run, kdb, package_root, keyrings,
                                       pocket)

    if spnames_only:
        log.info('Running in SourcePackageName-only mode...')
        for source in packages_map.src_map.itervalues():
            log.info('Ensuring %s name' % source['Package'])
            importer_handler.import_sourcepackagename(source['Package'])
        log.info('done')
        sys.exit(0)

    import_sourcepackages(packages_map, kdb, package_root, keyrings,
                          importer_handler)
    importer_handler.publish_sourcepackages(pocket)
    importer_handler.commit()

    if source_only:
        log.info('Source only mode... Done')
        sys.exit(0)

    import_binarypackages(pocket, packages_map, kdb, package_root,
                          keyrings, importer_handler)
    importer_handler.publish_binarypackages(pocket)
    importer_handler.commit()


def import_sourcepackages(packages_map, kdb, package_root,
                          keyrings, importer_handler):
    # Goes over src_map importing the sourcepackages packages.
    count = 0
    npacks = len(packages_map.src_map)
    log.info('%i Source Packages to be imported' % npacks)

    for source in packages_map.src_map.itervalues():
        count += 1
        do_one_sourcepackage(source, kdb, package_root, keyrings,
                             importer_handler)

        if COUNTDOWN and count % COUNTDOWN == 0:
            log.warn('%i/%i sourcepackages processed' % (count, npacks))

        # Commit often or hold locks in the database!
        importer_handler.commit()


def do_one_sourcepackage(source, kdb, package_root, keyrings,
                         importer_handler):
    try:
        source_data = SourcePackageData(**source)
    except MissingRequiredArguments:
        log.exception("Unable to create SourcePackageData for %s: "
                      "Required attributes not found" % 
                      source.get("Package", "unknown"))
        return
    except psycopg.Error:
        log.exception("Database error: unable to create "
                      "SourcePackageData for %s" %
                      source.get("Package", "unknown"))
        importer_handler.abort()
        return
    except (AttributeError, KeyError, ValueError, TypeError):
        # XXX: Debonzi 20050720
        # Catch all common exception since they are not predictable ATM.
        # SourcePackageData class should be refactored or rewrited to try
        # to make it better and have tested include.
        log.exception("Unable to create SourcePackageData for %s" %
                      source.get("Package", "unknown"))
        return

    if importer_handler.preimport_sourcecheck(source_data):
        # Don't bother reading package information if the source package
        # already exists in the database
        log.debug('%s already exists' % source_data.package)
        return

    try:
        source_data.process_package(kdb, package_root, keyrings)
    except PackageFileProcessError:
        # Problems with katie db stuff of opening files
        log.exception("Error processing package files for %s" % 
                      source_data.package)
        return

    source_data.ensure_complete(kdb)

    # XXX The check if this package already exists is done twice here,
    # since preimport_sourcecheck already does it. -- kiko, 2005-10-18
    importer_handler.import_sourcepackage(source_data)


def import_binarypackages(pocket, packages_map, kdb, package_root,
                          keyrings, importer_handler):
    nosource = []

    # Runs over all the architectures we have
    for arch in packages_map.bin_map.keys():
        count = 0
        npacks = len(packages_map.bin_map[arch])
        log.info('%i Binary Packages to be imported for %s' % 
                 (npacks, arch))
        # Go over the binarypackages map importing them for this architecture
        for binary in packages_map.bin_map[arch].itervalues():
            count += 1

            do_one_binarypackage(binary, arch, kdb, package_root, keyrings,
                                 importer_handler, nosource)

            if COUNTDOWN and count % COUNTDOWN == 0:
                log.warn('%i/%i binary packages processed' % (count, npacks))

        if nosource:
            log.warn('%i Sources Not Found' % len(nosource))
            for pkg in nosource:
                log.warn(pkg)

        importer_handler.commit()


def do_one_binarypackage(binary, arch, kdb, package_root, keyrings,
                         importer_handler, nosource):
    try:
        binary_data = BinaryPackageData(**binary)
    except MissingRequiredArguments:
        # Required attributes for this instance was not found.
        log.exception("Unable to create BinaryPackageData: "
                      "required attributes missing")
    except psycopg.Error:
        log.exception("Database error: unable to create "
                      "BinaryPackageData")
        importer_handler.abort()
    except (AttributeError, ValueError, KeyError, TypeError):
        # XXX: Debonzi 20050720
        # Catch all common exception since they are not
        # predictable ATM. BinaryPackageData class should be
        # refactored or rewritten to try to make it better and
        # have tests included.
        log.exception("Failed to create BinaryPackageData")
        return

    binary_data.ensure_complete(kdb)

    if not binary_data.process_package(kdb, package_root, keyrings):
        # Problems with katie db stuff of opening files
        log.error('Failed to import %s' % binary_data.package)
        return

    log.debug('Checking %s' % binary_data.package)
    try:
        if not importer_handler.import_binarypackage(arch, binary_data):
            msg = 'Sourcepackage %s (%s) not found for %s (%s)' % (
                    binary_data.source, binary_data.source_version,
                    binary_data.package, binary_data.version,)

            log.info(msg)
            nosource.append(msg)
    except (AttributeError, ValueError, TypeError):
        log.exception("Failed to import_binarypackage")
    except psycopg.Error:
        log.exception("Database error. Failed to import_binarypackage")
        importer_handler.abort()

    # Commit often or else we hold locks in the database
    importer_handler.commit()


if __name__ == "__main__":
    main()

