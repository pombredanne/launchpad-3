#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: 7c138a54-eee4-48b5-80ff-c8bf8df5b9a3
"""Sourcerer Importer.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os
import sys
import logging

import lib
import lib.debian
import soyuzwrapper as soyuz


class ImporterFailure(Exception): pass


def run_import(log, dsc, man_in=None, man_out=None, readonly=False,
               rollback=None):
    log.info("Starting %s", dsc)
    inventory = lib.debian.inventory.DebianInventory(dsc, log_parent=log)

    # Get the source package from the database, or create a new one
    pkg = soyuz.getSourcePackage(inventory.package)
    if pkg is not None:
        log.info("Found existing source package record")
        if pkg.getRelease(inventory.version) is not None:
            raise ImporterFailure, "This release of source package " \
                  "has already been imported"
    else:
        log.info("Creating new source package record")
        pkg = soyuz.createSourcePackage(inventory.package)

    # Get the current manifest and update it against the inventory
    release = pkg.createRelease(inventory.version)
    manifest = release.getManifest()
    if man_in is not None:
        log.info("Reading manifest from %s", man_in)
        man_file = open(man_in, "r")
        manifest.read(man_file)
        man_file.close()
    lib.manifest.update_manifest(manifest, inventory, log_parent=log)

    # Pass the manifest to the importer
    imp = lib.importer.Importer(os.path.dirname(dsc), manifest, log_parent=log,
                                rollback=rollback)

    # Save the manifest
    if man_out is not None:
        log.info("Writing manifest to %s", man_out)
        man_file = open(man_out, "w")
        manifest.write(man_file)
        man_file.close()
    if not readonly:
        # FIXME: Save the manifest to the database!
        pass

    log.info("Finished %s", dsc)


def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    readonly = False
    dsc = man_in = man_out = None
    for arg in sys.argv[1:]:
        if arg.startswith("--in="):
            man_in = arg[5:]
        elif arg.startswith("--out="):
            man_out = arg[6:]
        elif arg == "--readonly":
            readonly = True
        elif arg.startswith("-"):
            print >>sys.stderr, "Unknown Option:", arg
            print >>sys.stderr, "--in=MANIFEST    Read manifest from file"
            print >>sys.stderr, "--out=MANIFEST   Write manifest to file"
            print >>sys.stderr, "--readonly       Don't write to database"
            sys.exit(1)
        elif dsc is None:
            dsc = arg
        else:
            print >>sys.stderr, "Too many arguments:", arg
            sys.exit(1)

    pkg = dsc[:dsc.index("_")]
    log = logging.getLogger(pkg)

    run_import(log, dsc, man_in, man_out, readonly)


if __name__ == "__main__":
    main()
