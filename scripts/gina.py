#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

"""Gina Class.

Main gina class. handle the options and make the proper calls to the
other classes and instances.
"""
__all__ = ['Gina',]

import os, sys
from string import split

from canonical.launchpad.scripts.gina.database import Katie
from canonical.launchpad.scripts.gina.archive import (ArchiveComponentItems,
                                                      PackagesMap)

from canonical.launchpad.scripts.gina.handlers import ImporterHandler
from canonical.launchpad.scripts.gina.packages import (SourcePackageData, 
                                                       BinaryPackageData)

from canonical.lp.dbschema import PackagePublishingPocket
from canonical.config import config

def main(options):
    package_root = options.package_root
    keyrings_root = options.keyrings_root
    distro = options.distro
    distrorelease = options.distrorelease
    components = options.components.split(",")
    archs = options.archs.split(",")
    pocket = options.pocket
    pocket_distrorelease = options.pocket_distrorelease
    dry_run = options.dry_run
    source_only = options.source_only
    spnames_only = options.spnames_only
    LPDB = config.dbname
    LPDB_HOST = config.dbhost
    LPDB_USER = config.gina.dbuser
    KTDB = options.katie

    if hasattr(PackagePublishingPocket, pocket.upper()):
        pocket = getattr(PackagePublishingPocket, pocket.upper())
    else:
        print (' ** Could not found a correspondent pocket schema for %s\n'
               'Exiting...'
               %pocket)
        sys.exit(0)

    if not pocket_distrorelease:
        pocket_distrorelease = distrorelease

    LIBRHOST = config.librarian.upload_host
    LIBRPORT = config.librarian.upload_port
        
    print "$ Packages read from: %s" % package_root
    print "$ Keyrings read from: %s" % keyrings_root
    print "$ Archive to read: %s/%s" % (distro,distrorelease)
    print "$ Destine DistroRelease/Pocket: %s/%s"%(pocket_distrorelease,
                                                  pocket.title.lower())
    print "$ Components to import: %s" % ", ".join(components)
    print "$ Architectures to import: %s" % ", ".join(archs)
    print "$ Launchpad database: %s" % LPDB
    print "$ Launchpad database host: %s" % LPDB_HOST
    print "$ Launchpad database user: %s" % LPDB_USER
    print "$ Katie database: %s" % KTDB
    print "$ SourcePackage Only: %s" %source_only
    print "$ SourcePackageName Only: %s" %spnames_only
    print "$ Librarian: %s:%s" % (LIBRHOST,LIBRPORT)
    print "$ Dry run: %s" % (dry_run)
    
    if not options.run:
        print "* Specify --run to actually run, --help to see help"
        sys.exit(0)
        
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
        print 'Source only mode... Done'
        sys.exit(0)

    if spnames_only:
        print 'SoucePackageNames only mode... Done'
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
    print '****** %i SourcePackages to be imported'%npacks
    
    for source in packages_map.src_map.itervalues():

        # If spnames flag is true, do it as fast as you can.
        if spnames_only:
            print '   ** Ensuring %s name'%source['Package']
            importer_handler.import_sourcepackagename(source['Package'])
            print '                                  ... Done'
            continue

        source_data = SourcePackageData(kdb, **source)

        print ('Check Sourcepackage %s Version %s before process it'
               %(source_data.package, source_data.version))

        if importer_handler.preimport_sourcecheck(source_data):
            print '   * %s Already exists'%source_data.package
        else:
            if not source_data.process_package(kdb, package_root,
                                       keyrings):
                # Problems with katie db stuff of opening files
                print '   * Failed to import %s', source_data.package
                npacks -= 1
                continue

            importer_handler.import_sourcepackage(source_data)
        count += 1
        npacks -= 1
        if count > 10:
            count = 0
            print '****** Count down is %i sourcepackages'%npacks
            importer_handler.commit()

def import_binarypackages(pocket, packages_map, kdb, package_root,
                          keyrings, importer_handler):
    
    #
    # Binaries Import
    #

    nosource = 0
    messages = []
    count = 0

    # Runs over all the architectures we have
    for arch in packages_map.bin_map.keys():
        countdown = len(packages_map.bin_map[arch])
        print ('****** %i Binarypackage to be imported for %s'
               %(countdown, arch))
        # Goes over the binarypackages map importing them
        # for this architecture.
        for binary in packages_map.bin_map[arch].itervalues():
            binary_data = BinaryPackageData(**binary)

            if not binary_data.process_package(kdb, package_root,
                                               keyrings):
                # Problems with katie db stuff of opening files
                print '   * Failed to import %s', binary_data.package
                countdown -= 1
                continue

            count += 1
            print 'Checking %s'%binary_data.package
            if not importer_handler.import_binarypackage(arch,
                                                              binary_data):
                msg = ('Sourcepackage %s (%s) not found for %s (%s)'
                       %(binary_data.source, binary_data.source_version,
                         binary_data.package, binary_data.version))

                print msg
                messages.append(msg)
                nosource += 1
            if count > 9:
                count = 0
                print '**************** Countdoun %i'%countdown
                importer_handler.commit()
            countdown -= 1
        if nosource:
            print '%i Sources Not Found'%nosource
            for pkg in messages:
                print pkg
        importer_handler.commit()
    importer_handler.publish_binarypackages(pocket)
    importer_handler.commit()


if __name__ == "__main__":
    from canonical.launchpad.scripts.gina.options import options

    main(options)
