#!/usr/bin/python -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This module uses relative imports.
# pylint: disable-msg=W0403

"""
Gina launcher script. Handles commandline options and makes the proper
calls to the other classes and instances.

The callstack is essentially:
    main -> run_gina
                -> import_sourcepackages -> do_one_sourcepackage
                -> import_binarypackages -> do_one_binarypackage
"""


__metaclass__ = type

import os
import sys
import time

import _pythonpath
import psycopg2
from zope.component import getUtility

from canonical import lp
from canonical.config import config
from canonical.launchpad.scripts import log
from lp.services.scripts.base import LaunchpadCronScript
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.scripts.gina import ExecutionError
from lp.soyuz.scripts.gina.archive import (
    ArchiveComponentItems,
    MangledArchiveError,
    PackagesMap,
    )
from lp.soyuz.scripts.gina.dominate import dominate_imported_source_packages
from lp.soyuz.scripts.gina.handlers import (
    DataSetupError,
    ImporterHandler,
    MultiplePackageReleaseError,
    NoSourcePackageError,
    )
from lp.soyuz.scripts.gina.katie import Katie
from lp.soyuz.scripts.gina.packages import (
    BinaryPackageData,
    DisplayNameDecodingError,
    InvalidVersionError,
    MissingRequiredArguments,
    PoolFileNotFound,
    SourcePackageData,
    )

# Set to non-zero if you'd like to be warned every so often
COUNTDOWN = 0


def _get_keyring(keyrings_root):
    # XXX kiko 2005-10-23: untested
    keyrings = ""
    for keyring in os.listdir(keyrings_root):
        path = os.path.join(keyrings_root, keyring)
        keyrings += " --keyring=%s" % path
    if not keyrings:
        raise AttributeError("Keyrings not found in ./keyrings/")
    return keyrings


def run_gina(options, ztm, target_section):
    # Avoid circular imports.
    from lp.registry.interfaces.pocket import PackagePublishingPocket

    package_root = target_section.root
    keyrings_root = target_section.keyrings
    distro = target_section.distro
    # XXX kiko 2005-10-23: I honestly think having a separate distroseries
    # bit silly. Can't we construct this based on `distroseries-pocket`?
    pocket_distroseries = target_section.pocketrelease
    distroseries = target_section.distroseries
    components = [c.strip() for c in target_section.components.split(",")]
    archs = [a.strip() for a in target_section.architectures.split(",")]
    pocket = target_section.pocket
    component_override = target_section.componentoverride
    source_only = target_section.source_only
    spnames_only = target_section.sourcepackagenames_only

    dry_run = options.dry_run

    LPDB = lp.get_dbname()
    LPDB_HOST = lp.dbhost
    LPDB_USER = config.gina.dbuser
    KTDB = target_section.katie_dbname

    LIBRHOST = config.librarian.upload_host
    LIBRPORT = config.librarian.upload_port

    log.info("")
    log.info("=== Processing %s/%s/%s ===", distro, distroseries, pocket)
    log.debug("Packages read from: %s", package_root)
    log.debug("Keyrings read from: %s", keyrings_root)
    log.info("Components to import: %s", ", ".join(components))
    if component_override is not None:
        log.info("Override components to: %s", component_override)
    log.info("Architectures to import: %s", ", ".join(archs))
    log.debug("Launchpad database: %s", LPDB)
    log.debug("Launchpad database host: %s", LPDB_HOST)
    log.debug("Launchpad database user: %s", LPDB_USER)
    log.info("Katie database: %s", KTDB)
    log.info("SourcePackage Only: %s", source_only)
    log.info("SourcePackageName Only: %s", spnames_only)
    log.debug("Librarian: %s:%s", LIBRHOST, LIBRPORT)
    log.info("Dry run: %s", dry_run)
    log.info("")

    if not hasattr(PackagePublishingPocket, pocket.upper()):
        log.error("Could not find a pocket schema for %s", pocket)
        sys.exit(1)

    pocket = getattr(PackagePublishingPocket, pocket.upper())

    if component_override:
        valid_components = [
            component.name for component in getUtility(IComponentSet)]
        if component_override not in valid_components:
            log.error("Could not find component %s", component_override)
            sys.exit(1)

    kdb = None
    keyrings = None
    if KTDB:
        kdb = Katie(KTDB, distroseries, dry_run)
        keyrings = _get_keyring(keyrings_root)

    try:
        arch_component_items = ArchiveComponentItems(
            package_root, pocket_distroseries, components, archs,
            source_only)
    except MangledArchiveError:
        log.exception(
            "Failed to analyze archive for %s", pocket_distroseries)
        sys.exit(1)

    packages_map = PackagesMap(arch_component_items)
    importer_handler = ImporterHandler(
        ztm, distro, distroseries, dry_run, kdb, package_root, keyrings,
        pocket, component_override)

    import_sourcepackages(
        packages_map, kdb, package_root, keyrings, importer_handler)
    importer_handler.commit()

    # XXX JeroenVermeulen 2011-09-07 bug=843728: Dominate binaries as well.
    dominate_imported_source_packages(
        log, distro, distroseries, pocket, packages_map)

    if source_only:
        log.info('Source only mode... done')
        return

    for archtag in archs:
        try:
            importer_handler.ensure_archinfo(archtag)
        except DataSetupError:
            log.exception("Database setup required for run on %s", archtag)
            sys.exit(1)

    import_binarypackages(
        packages_map, kdb, package_root, keyrings, importer_handler)
    importer_handler.commit()


def attempt_source_package_import(source, kdb, package_root, keyrings,
                                  importer_handler):
    """Attempt to import a source package, and handle typical errors."""
    package_name = source.get("Package", "unknown")
    try:
        try:
            do_one_sourcepackage(
                source, kdb, package_root, keyrings, importer_handler)
        except psycopg2.Error:
            log.exception(
                "Database error: unable to create SourcePackage for %s. "
                "Retrying once..", package_name)
            importer_handler.abort()
            time.sleep(15)
            do_one_sourcepackage(
                source, kdb, package_root, keyrings, importer_handler)
    except (
        InvalidVersionError, MissingRequiredArguments,
        DisplayNameDecodingError):
        log.exception(
            "Unable to create SourcePackageData for %s", package_name)
    except (PoolFileNotFound, ExecutionError):
        # Problems with katie db stuff of opening files
        log.exception("Error processing package files for %s", package_name)
    except psycopg2.Error:
        log.exception(
            "Database errors made me give up: unable to create "
            "SourcePackage for %s", package_name)
        importer_handler.abort()
    except MultiplePackageReleaseError:
        log.exception(
            "Database duplication processing %s", package_name)


def import_sourcepackages(packages_map, kdb, package_root,
                          keyrings, importer_handler):
    # Goes over src_map importing the sourcepackages packages.
    count = 0
    npacks = len(packages_map.src_map)
    log.info('%i Source Packages to be imported', npacks)

    for package in sorted(packages_map.src_map.iterkeys()):
        for source in packages_map.src_map[package]:
            count += 1
            attempt_source_package_import(
                source, kdb, package_root, keyrings, importer_handler)
            if COUNTDOWN and (count % COUNTDOWN == 0):
                log.warn('%i/%i sourcepackages processed', count, npacks)


def do_one_sourcepackage(source, kdb, package_root, keyrings,
                         importer_handler):
    source_data = SourcePackageData(**source)
    if importer_handler.preimport_sourcecheck(source_data):
        # Don't bother reading package information if the source package
        # already exists in the database
        log.info('%s already exists in the archive', source_data.package)
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
        log.info(
            '%i Binary Packages to be imported for %s', npacks, archtag)
        # Go over binarypackages importing them for this architecture
        for package_name in sorted(packages_map.bin_map[archtag].iterkeys()):
            binary = packages_map.bin_map[archtag][package_name]
            count += 1
            try:
                try:
                    do_one_binarypackage(binary, archtag, kdb, package_root,
                                         keyrings, importer_handler)
                except psycopg2.Error:
                    log.exception(
                        "Database errors when importing a BinaryPackage "
                        "for %s. Retrying once..", package_name)
                    importer_handler.abort()
                    time.sleep(15)
                    do_one_binarypackage(binary, archtag, kdb, package_root,
                                         keyrings, importer_handler)
            except (InvalidVersionError, MissingRequiredArguments):
                log.exception(
                    "Unable to create BinaryPackageData for %s", package_name)
                continue
            except (PoolFileNotFound, ExecutionError):
                # Problems with katie db stuff of opening files
                log.exception(
                    "Error processing package files for %s", package_name)
                continue
            except MultiplePackageReleaseError:
                log.exception(
                    "Database duplication processing %s", package_name)
                continue
            except psycopg2.Error:
                log.exception(
                    "Database errors made me give up: unable to create "
                    "BinaryPackage for %s", package_name)
                importer_handler.abort()
                continue
            except NoSourcePackageError:
                log.exception(
                    "Failed to create Binary Package for %s", package_name)
                nosource.append(binary)
                continue

            if COUNTDOWN and count % COUNTDOWN == 0:
                # XXX kiko 2005-10-23: untested
                log.warn('%i/%i binary packages processed', count, npacks)

        if nosource:
            # XXX kiko 2005-10-23: untested
            log.warn('%i source packages not found', len(nosource))
            for pkg in nosource:
                log.warn(pkg)


def do_one_binarypackage(binary, archtag, kdb, package_root, keyrings,
                         importer_handler):
    binary_data = BinaryPackageData(**binary)
    if importer_handler.preimport_binarycheck(archtag, binary_data):
        log.info('%s already exists in the archive', binary_data.package)
        return
    binary_data.process_package(kdb, package_root, keyrings)
    importer_handler.import_binarypackage(archtag, binary_data)
    importer_handler.commit()


class Gina(LaunchpadCronScript):

    def __init__(self):
        super(Gina, self).__init__(name='gina', dbuser=config.gina.dbuser)

    @property
    def usage(self):
        return "%s [options] (targets|--all)" % sys.argv[0]

    def add_my_options(self):
        self.parser.add_option("-a", "--all", action="store_true",
            help="Run all sections defined in launchpad.conf (in order)",
            dest="all", default=False)
        self.parser.add_option("-l", "--list-targets", action="store_true",
            help="List configured import targets", dest="list_targets",
            default=False)
        self.parser.add_option("-n", "--dry-run", action="store_true",
            help="Don't commit changes to the database",
            dest="dry_run", default=False)

    def getConfiguredTargets(self):
        """Get the configured import targets.

        Gina's targets are configured as "[gina_target.*]" sections in the
        LAZR config.
        """
        sections = config.getByCategory('gina_target', [])
        targets = [
            target.category_and_section_names[1] for target in sections]
        if len(targets) == 0:
            self.logger.warn("No gina_target entries configured.")
        return targets

    def listTargets(self, targets):
        """Print out the given targets list."""
        for target in targets:
            self.logger.info("Target: %s", target)

    def getTargets(self, possible_targets):
        """Get targets to process."""
        targets = self.args
        if self.options.all:
            return list(possible_targets)
        else:
            if not targets:
                self.parser.error(
                    "Must specify at least one target to run, or --all")
            for target in targets:
                if target not in possible_targets:
                    self.parser.error(
                        "No Gina target %s in config file" % target)
            return targets

    def main(self):
        possible_targets = self.getConfiguredTargets()

        if self.options.list_targets:
            self.listTargets(possible_targets)
            return

        for target in self.getTargets(possible_targets):
            target_section = config['gina_target.%s' % target]
            run_gina(self.options, self.txn, target_section)


if __name__ == "__main__":
    gina = Gina()
    gina.lock_and_run()
