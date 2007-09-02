#!/usr/bin/python2.4
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
import time
import psycopg
from optparse import OptionParser
from datetime import timedelta

from zope.component import getUtility

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.lp import initZopeless, dbschema
from canonical.config import config
from canonical.launchpad.interfaces import IComponentSet
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, log)

from canonical.launchpad.scripts.gina import ExecutionError
from canonical.launchpad.scripts.gina.katie import Katie
from canonical.launchpad.scripts.gina.archive import (ArchiveComponentItems,
    PackagesMap, MangledArchiveError)

from canonical.launchpad.scripts.gina.handlers import (ImporterHandler,
    MultiplePackageReleaseError, NoSourcePackageError, DataSetupError)
from canonical.launchpad.scripts.gina.packages import (SourcePackageData,
    BinaryPackageData, MissingRequiredArguments, DisplayNameDecodingError,
    PoolFileNotFound, InvalidVersionError)


def _get_keyring(keyrings_root):
    # XXX kiko 2005-10-23: untested
    keyrings = ""
    for keyring in os.listdir(keyrings_root):
        path = os.path.join(keyrings_root, keyring)
        keyrings += " --keyring=%s" % path
    if not keyrings:
        raise AttributeError("Keyrings not found in ./keyrings/")
    return keyrings


def main():
    execute_zcml_for_scripts()
    parser = OptionParser("Usage: %prog [OPTIONS] [target ...]")
    logger_options(parser)

    parser.add_option("-n", "--dry-run", action="store_true",
            help="Don't commit changes to the database",
            dest="dry_run", default=False)

    parser.add_option("-a", "--all", action="store_true",
            help="Run all sections defined in launchpad.conf (in order)",
            dest="all", default=False)

    parser.add_option( "-l", "--lockfile", 
            default="/var/lock/launchpad-gina.lock",
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

    lockfile = GlobalLock(options.lockfile, logger=log)
    try:
        lockfile.acquire()
    except LockAlreadyAcquired:
        log.info('Lockfile %s already locked. Exiting.', options.lockfile)
        sys.exit(1)

    ztm = initZopeless(dbuser=config.gina.dbuser)
    try:
        for target in targets:
            target_sections = [section for section in config.gina.target
                               if section.getSectionName() == target]
            # XX kiko, 2005-10-18X: should be a proper exception.
            assert len(target_sections) == 1
            run_gina(options, ztm, target_sections[0])
    finally:
        lockfile.release()


def run_gina(options, ztm, target_section):
    package_root = target_section.root
    keyrings_root = target_section.keyrings
    distro = target_section.distro
    # XXX kiko 2005-10-23: I honestly think having a separate distrorelease
    # bit silly. Can't we construct this based on `distrorelease-pocket`?
    pocket_distrorelease = target_section.pocketrelease
    distrorelease = target_section.distrorelease
    components = [c.strip() for c in target_section.components.split(",")]
    archs = [a.strip() for a in target_section.architectures.split(",")]
    pocket = target_section.pocket
    component_override = target_section.componentoverride
    source_only = target_section.source_only
    spnames_only = target_section.sourcepackagenames_only

    dry_run = options.dry_run

    LPDB = config.dbname
    LPDB_HOST = config.dbhost
    LPDB_USER = config.gina.dbuser
    KTDB = target_section.katie_dbname

    LIBRHOST = config.librarian.upload_host
    LIBRPORT = config.librarian.upload_port

    log.info("")
    log.info("=== Processing %s/%s/%s ===" % (distro, distrorelease, pocket))
    log.debug("Packages read from: %s" % package_root)
    log.debug("Keyrings read from: %s" % keyrings_root)
    log.info("Components to import: %s" % ", ".join(components))
    if component_override is not None:
        log.info("Override components to: %s" % component_override)
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

    if hasattr(dbschema.PackagePublishingPocket, pocket.upper()):
        pocket = getattr(dbschema.PackagePublishingPocket, pocket.upper())
    else:
        log.error("Could not find a pocket schema for %s" % pocket)
        sys.exit(1)

    if component_override:
        valid_components = [
            component.name for component in getUtility(IComponentSet)]
        if component_override not in valid_components:
            log.error("Could not find component %s" % component_override)
            sys.exit(1)

    kdb = None
    keyrings = None
    if KTDB:
        kdb = Katie(KTDB, distrorelease, dry_run)
        keyrings = _get_keyring(keyrings_root)

    try:
        arch_component_items = ArchiveComponentItems(package_root,
                                                     pocket_distrorelease,
                                                     components, archs)
    except MangledArchiveError:
        log.exception("Failed to analyze archive for %s" % pocket_distrorelease)
        sys.exit(1)

    packages_map = PackagesMap(arch_component_items)
    importer_handler = ImporterHandler(ztm, distro, distrorelease,
                                       dry_run, kdb, package_root, keyrings,
                                       pocket, component_override)

    for archtag in archs:
        try:
            importer_handler.ensure_archinfo(archtag)
        except DataSetupError:
            log.exception("Database setup required for run on %s" % archtag)
            sys.exit(1)

    if spnames_only:
        log.info('Running in SourcePackageName-only mode...')
        for source in packages_map.src_map.itervalues():
            log.info('Ensuring %s name' % source['Package'])
            importer_handler.ensure_sourcepackagename(source['Package'])
        log.info('done')
        sys.exit(0)

    import_sourcepackages(packages_map, kdb, package_root, keyrings,
                          importer_handler)
    importer_handler.commit()

    if source_only:
        log.info('Source only mode... done')
        sys.exit(0)

    import_binarypackages(packages_map, kdb, package_root, keyrings,
                          importer_handler)
    importer_handler.commit()


def import_sourcepackages(packages_map, kdb, package_root,
                          keyrings, importer_handler):
    # Goes over src_map importing the sourcepackages packages.
    count = 0
    npacks = len(packages_map.src_map)
    log.info('%i Source Packages to be imported' % npacks)

    for source in sorted(packages_map.src_map.values(),
                         key=lambda x: x.get("Package")):
        count += 1
        package_name = source.get("Package", "unknown")
        try:
            try:
                do_one_sourcepackage(source, kdb, package_root, keyrings,
                                     importer_handler)
            except psycopg.Error:
                log.exception("Database error: unable to create "
                              "SourcePackage for %s. Retrying once.."
                              % package_name)
                importer_handler.abort()
                time.sleep(15)
                do_one_sourcepackage(source, kdb, package_root, keyrings,
                                     importer_handler)
        except (InvalidVersionError, MissingRequiredArguments,
                DisplayNameDecodingError):
            log.exception("Unable to create SourcePackageData for %s" % 
                          package_name)
            continue
        except (PoolFileNotFound, ExecutionError):
            # Problems with katie db stuff of opening files
            log.exception("Error processing package files for %s" %
                          package_name)
            continue
        except psycopg.Error:
            log.exception("Database errors made me give up: unable to create "
                          "SourcePackage for %s" % package_name)
            importer_handler.abort()
            continue
        except MultiplePackageReleaseError:
            log.exception("Database duplication processing %s" %
                          package_name)
            continue

        if COUNTDOWN and count % COUNTDOWN == 0:
            log.warn('%i/%i sourcepackages processed' % (count, npacks))


def do_one_sourcepackage(source, kdb, package_root, keyrings,
                         importer_handler):
    source_data = SourcePackageData(**source)
    if importer_handler.preimport_sourcecheck(source_data):
        # Don't bother reading package information if the source package
        # already exists in the database
        log.info('%s already exists in the archive' % source_data.package)
        return
    source_data.process_package(kdb, package_root, keyrings)
    source_data.ensure_complete(kdb)
    importer_handler.import_sourcepackage(source_data)
    importer_handler.commit()


def import_binarypackages(packages_map, kdb, package_root, keyrings,
                          importer_handler):
    nosource = []

    # Run over all the architectures we have
    for archtag in packages_map.bin_map.keys():
        count = 0
        npacks = len(packages_map.bin_map[archtag])
        log.info('%i Binary Packages to be imported for %s' % 
                 (npacks, archtag))
        # Go over binarypackages importing them for this architecture
        for binary in sorted(packages_map.bin_map[archtag].values(),
                             key=lambda x: x.get("Package")):
            count += 1
            package_name = binary.get("Package", "unknown")
            try:
                try:
                    do_one_binarypackage(binary, archtag, kdb, package_root,
                                         keyrings, importer_handler)
                except psycopg.Error:
                    log.exception("Database errors when importing a "
                                  "BinaryPackage for %s. Retrying once.."
                                  % package_name)
                    importer_handler.abort()
                    time.sleep(15)
                    do_one_binarypackage(binary, archtag, kdb, package_root,
                                         keyrings, importer_handler)
            except (InvalidVersionError, MissingRequiredArguments):
                log.exception("Unable to create BinaryPackageData for %s" % 
                              package_name)
                continue
            except (PoolFileNotFound, ExecutionError):
                # Problems with katie db stuff of opening files
                log.exception("Error processing package files for %s" %
                              package_name)
                continue
            except MultiplePackageReleaseError:
                log.exception("Database duplication processing %s" %
                              package_name)
                continue
            except psycopg.Error:
                log.exception("Database errors made me give up: unable to "
                              "create BinaryPackage for %s" % package_name)
                importer_handler.abort()
                continue
            except NoSourcePackageError:
                log.exception("Failed to create Binary Package for %s" % 
                              package_name)
                nosource.append(binary)
                continue

            if COUNTDOWN and count % COUNTDOWN == 0:
                # XXX kiko 2005-10-23: untested
                log.warn('%i/%i binary packages processed' % (count, npacks))

        if nosource:
            # XXX kiko 2005-10-23: untested
            log.warn('%i source packages not found' % len(nosource))
            for pkg in nosource:
                log.warn(pkg)


def do_one_binarypackage(binary, archtag, kdb, package_root, keyrings,
                         importer_handler):
    binary_data = BinaryPackageData(**binary)
    if importer_handler.preimport_binarycheck(archtag, binary_data):
        log.info('%s already exists in the archive' % binary_data.package)
        return
    binary_data.process_package(kdb, package_root, keyrings)
    importer_handler.import_binarypackage(archtag, binary_data)
    importer_handler.commit()


if __name__ == "__main__":
    main()

