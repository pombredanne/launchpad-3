#!/usr/bin/env python

import apt_pkg, tempfile, os, tempfile, shutil, sys

from classes import SourcePackageRelease, BinaryPackageRelease
from database import Launchpad, Katie, LaunchpadTester
from library import attachLibrarian

from traceback import print_exc as printexception

from optparse import OptionParser

# Parse the commandline...

parser = OptionParser()
parser.add_option("-r","--root", dest="package_root",
                  help="read archive from ROOT",
                  metavar="ROOT",
                  default="/srv/archive.ubuntu.com/ubuntu/")

parser.add_option("-k","--keyrings", dest="keyrings_root",
                  help="read keyrings from KEYRINGS",
                  metavar="KEYRINGS",
                  default="keyrings/")

parser.add_option("-D","--distro", dest="distro",
                  help="import into DISTRO",
                  metavar="DISTRO",
                  default="ubuntu")

parser.add_option("-d","--distrorelease", dest="distrorelease",
                  help="import into DISTRORELEASE",
                  metavar="DISTRORELEASE",
                  default="warty")

parser.add_option("-c","--components", dest="components",
                  help="import COMPONENTS components",
                  metavar="COMPONENTS",
                  default="main,restricted,universe")

parser.add_option("-a", "--arch", dest="archs",
                  help="import ARCHS architectures",
                  metavar="ARCHS",
                  default="i386,powerpc,amd64")

parser.add_option("-l", "--launchpad", dest="launchpad",
                  help="use LPDB as the launchpad database",
                  metavar="LPDB",
                  default="launchpad_dogfood")

parser.add_option("-K", "--katie", dest="katie",
                  help="use KTDB as the katie database for DISTRO",
                  metavar="KTDB",
                  default="katie")

parser.add_option("-L", "--librarian", dest="librarian",
                  help="use HOST:PORT as the librarian",
                  metavar="HOST:PORT",
                  default="localhost:9090")

parser.add_option("-R", "--run", dest="run",
                  help="actually do the run",
                  default=False, action='store_true')

parser.add_option("-n", "--dry-run", dest="dry_run",
                  help="don't commit changes to database",
                  default=False, action='store_true')

parser.add_option("-b", "--back-propagate", dest="back_propagate",
                  help="Make package back propagation",
                  default=False, action='store_true')

parser.add_option("-s", "--source-only", dest="source_only",
                  help="Import only Source Packages",
                  default=False, action='store_true')

(options,args) = parser.parse_args()

package_root = options.package_root
keyrings_root = options.keyrings_root
distro = options.distro
distrorelease = options.distrorelease
components = options.components.split(",")
archs = options.archs.split(",")
LPDB = options.launchpad
KTDB = options.katie

(LIBRHOST, LIBRPORT) = options.librarian.split(":")
LIBRPORT = int(LIBRPORT)

print "$ Packages read from: %s" % package_root
print "$ Keyrings read from: %s" % keyrings_root
print "$ Archive to read: %s/%s" % (distro,distrorelease)
print "$ Components to import: %s" % ", ".join(components)
print "$ Architectures to import: %s" % ", ".join(archs)
print "$ Launchpad database: %s" % LPDB
print "$ Katie database: %s" % KTDB
print "$ Librarian: %s:%s" % (LIBRHOST,LIBRPORT)
print "$ Dry run: %s" % (options.dry_run)
print

if not options.run:
    print "* Specify --run to actually run, --help to see help"
    
    sys.exit(0)
    
#
# helpers
#
def get_tagfiles(root, distrorelease, component, arch):
    sources_zipped = os.path.join(root, "dists", distrorelease,
                                  component, "source", "Sources.gz")
    binaries_zipped = os.path.join(root, "dists", distrorelease,
                                   component, "binary-%s" % arch,
                                   "Packages.gz")
    di_zipped = os.path.join(root, "dists", distrorelease, component,
                             "debian-installer", "binary-%s" % arch,
                             "Packages.gz")
    
    srcfd, sources_tagfile = tempfile.mkstemp()
    os.system("gzip -dc %s > %s" % (sources_zipped, sources_tagfile))
    srcfile = os.fdopen(srcfd)

    binfd, binaries_tagfile = tempfile.mkstemp()
    os.system("gzip -dc %s > %s" % (binaries_zipped, binaries_tagfile))
    binfile = os.fdopen(binfd)

    difd, di_tagfile = tempfile.mkstemp()
    os.system("gzip -dc %s > %s" % (di_zipped, di_tagfile))
    difile = os.fdopen(difd)

    return (srcfile, sources_tagfile, binfile, binaries_tagfile, difile,
            di_tagfile)

def do_packages(source_map, bin_map, lp, kdb, keyrings, component, arch):
    try:
        srcfile, src_tags, binfile, bin_tags, difile, di_tags = \
            get_tagfiles(package_root, distrorelease, component, arch)

        sources = apt_pkg.ParseTagFile(srcfile)
        while sources.Step():
##             # To start from a given letter.
##             if dict(sources.Section)['Package'][0].lower()< 'p':
##                 continue
            srcpkg = SourcePackageRelease(kdb, component=component, 
                                          **dict(sources.Section))
            source_map[srcpkg.package] = srcpkg

        binaries = apt_pkg.ParseTagFile(binfile)
        while binaries.Step():
##             # To start from a given letter.
##             if dict(binaries.Section)['Package'][0].lower()< 'p':
##                 continue
            binpkg = BinaryPackageRelease(component=component, 
                                          **dict(binaries.Section))
            name = binpkg.package
            bin_map[name] = binpkg
            # source packages with the same name as binaries get descriptions
            # The binarypackage also gets a convenient link
            if source_map.has_key(name):
                source_map[name].description = binpkg.description
                binpkg.sourcepackageref = source_map[name]

        dibins = apt_pkg.ParseTagFile(difile)
        while dibins.Step():
##             # To start from a given letter.
##             if dict(dibins.Section)['Package'][0].lower()< 'p':
##                 continue

            binpkg = BinaryPackageRelease(component=component,
                                          filetype="udeb",
                                          **dict(dibins.Section))
            name = binpkg.package
            bin_map[name] = binpkg
            # source packages with the same name as binaries get descriptions
            # The binarypackage also gets a convenient link
            if source_map.has_key(name):
                source_map[name].description = binpkg.description
                binpkg.sourcepackageref = source_map[name]
                
    finally:
        os.unlink(bin_tags)
        os.unlink(src_tags)
        os.unlink(di_tags)

def do_sections(lp, kdb):
    sections = kdb.getSections()
    for section in sections:
        lp.addSection( section[0] )
        lp.commit()

def do_arch(lp, kdb, bin_map, source_map):
    # Loop through binaries and insert stuff in DB. We do this as a
    # separate loop mainly to ensure that all source packages get
    # preferentially the description relative to a homonymous binary
    # package, and if not, the first description tht pops up.
    bins = bin_map.items()
    bins.sort()
    count = 0
    for name, binpkg in bins:
        if not options.source_only:
            print "- Evaluating %s (%s, %s) for %s" % (binpkg.package, 
                                                       binpkg.component, 
                                                       binpkg.version,
                                                       binpkg.architecture)
            if not source_map.has_key(binpkg.source):
                # We check if we have a source package or else
                # binpkg.ensure_created() is going to die an ugly death
                print "\t** No source package parsed for %s" % binpkg.package
                continue

            if binpkg.is_created(lp):
                continue

        srcpkg = source_map[binpkg.source]

        if options.source_only:
            if srcpkg.is_created(lp):
                print ('- SourcePackageRelease %s-%s already imported'
                       % (srcpkg.package, srcpkg.version))
                continue

        if not srcpkg.is_processed:
            if not srcpkg.description:
                # if the source package hasn't had a description
                # set, set one now and hope for the best.
                srcpkg.description = binpkg.description
            # Tricky bit here: even if the source package exists, we
            # need to process it to ensure it has all the data inside it
            # or binary package won't create properly
##            try:

            # Daniel Debonzi 20050223
            # process_package is false when a package was not
            # found in katie db. AFAICS, there is not to do with
            # this package. Just give up.
            if not srcpkg.process_package(kdb, package_root, keyrings):
                print ('\t\t** Process Package Failed.'
                       ' Package not found in Katie DB')
                ## break
                continue

            srcpkg.ensure_created(lp)
##             except Exception, e:
##                 print "\t!! sourcepackage addition threw an error."
##                 printexception(e)
                # Since we're importing universe which can cause issues,
                # we don't exit
                # sys.exit(0)

        # we read the licence from the source package but it is
        # stored in the BinaryPackage table
        binpkg.licence = srcpkg.licence

        # If in source-only mode does not import the binary package
        # and does not create the build table.
        if options.source_only:
            continue

##        try:

        # Daniel Debonzi 20050223
        # process_package is false when a package was not
        # found in katie db. AFAICS, there is not to do with
        # this package. Just give up. The same as srcpkg.proccess_package
        # above.

        if not binpkg.process_package(kdb, package_root, keyrings):
                print '\t** Process Package Failed. Package not found in Katie DB'
                ## break
                continue
        binpkg.ensure_created(lp)
##         except Exception, e:
##             print "\t!! binarypackage addition threw an error."
##             printexception(e)
            # Since we're importing universe which can cause issues,
            # we don't exit
            # sys.exit(0)

        count = count + 1
        if count == 10:
            lp.commit()
            count = 0
            print "* Committed"


def do_publishing(pkgs, lp, source):
    for name, pkg in pkgs.items():
        if pkg.is_created(lp):
            if source:
                lp.publishSourcePackage(pkg)
            else:
                lp.publishBinaryPackage(pkg)

def do_backpropogation(kdb, lp, sources, keyrings):
    names = sources.keys() 
    # You can vary order here by doing names.sort() or names.reverse()
    names.sort()
    for srcpkg in names:
        if not sources[srcpkg].is_processed:
            sources[srcpkg].process_package(kdb, package_root, keyrings)
        sources[srcpkg].backpropogate(lp)


if __name__ == "__main__":
    # get the DB abstractors
    lp = {}
    for arch in archs:
        lp[arch] = Launchpad(LPDB, distro, distrorelease, arch, options.dry_run)
    kdb = Katie(KTDB, distrorelease, options.dry_run)

    # Comment this out if you need to disable the librarian integration
    # for a given run of gina. Note that without the librarian; lucille
    # will be unable to publish any files imported into the database
    attachLibrarian( LIBRHOST, LIBRPORT )

    keyrings = ""
    for keyring in os.listdir(keyrings_root):
        path = os.path.join(keyrings_root, keyring)
        keyrings += " --keyring=%s" % path
    if not keyrings:
        raise AttributeError, "Keyrings not found in ./keyrings/"

    # Validate that the supplied components are available...
    print "@ Validating components"
    for arch in archs:
        for comp in components:
            lp[arch].getComponentByName(comp)

    # Build us dicts of all package releases
    source_map = {}
    bin_map = {}
    for arch in archs:
        bin_map[arch] = {}
        for component in components:
            print "@ Loading components for %s/%s" % (arch,component)
            do_packages(source_map, bin_map[arch], lp[arch], kdb,
                        keyrings, component, arch)

    print "@ Loading sections"
    for arch in archs:
        do_sections(lp[arch], kdb)
    
    for arch in archs:
        do_arch(lp[arch],kdb,bin_map[arch],source_map)
        lp[arch].commit()


    if options.back_propagate:
        print "@ Performing backpropogation of sourcepackagerelease..."
        do_backpropogation(kdb, lp[archs[0]], source_map, keyrings)

    # Next empty the publishing tables...
    print "@ Emptying publishing tables..."
    src=True
    for arch in archs:
        lp[arch].emptyPublishing(src, options.source_only)
        lp[arch].commit()
        src=False

    print "@ Publishing source..."
    do_publishing(source_map, lp[archs[0]], True)
    lp[archs[0]].commit()

    # Source only mode. Does not mess with binary publishing.
    if not options.source_only:
        for arch in archs:
            print "@ Publishing %s binaries..." % arch
            do_publishing(bin_map[arch], lp[arch], False)
            lp[arch].commit()

    tester = LaunchpadTester(source_map, bin_map)
    tester.run()

    print "@ Closing database connections..."
    
    kdb.commit()
    kdb.close()

    print "@ Gina completed."
