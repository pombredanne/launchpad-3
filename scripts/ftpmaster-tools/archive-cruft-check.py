#!/usr/bin/env python

# Check for obsolete binary packages
# Copyright (C) 2006  James Troup <james.troup@canonical.com>
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005  James Troup <james@nocrew.org>

################################################################################

import commands
import optparse
import os
import string
import sys

import apt_pkg

import dak_utils

import _pythonpath

from zope.component import getUtility

from canonical.launchpad.database import DistroArchReleaseBinaryPackage
from canonical.launchpad.interfaces import (IBinaryPackageNameSet,
                                            IBinaryPackageReleaseSet,
                                            IDistributionSet, NotFoundError)
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
                                         logger, logger_options)
from canonical.lp import initZopeless

from contrib.glock import GlobalLock

################################################################################

Options = None
Log = None
Lock = None
Ztm = None
bpr = None
source_versions = None
source_binaries = None

################################################################################

def init():
    global Options, Log, Ztm, Lock, bpr

    apt_pkg.init()

    # Parse command-line arguments
    parser = optparse.OptionParser()
    logger_options(parser)
    parser.add_option("-d", "--distro", dest="distro",
                      help="remove from DISTRO")
    parser.add_option("-n", "--no-action", dest="action",
                      default=True, action="store_false",
                      help="don't do anything")
    parser.add_option("-s", "--suite", dest="distrorelease",
                      help="only act on SUITE")
    
    (Options, args) = parser.parse_args()
    Log = logger(Options, "archive-cruft-check")

    Log.debug("Acquiring lock")
    Lock = GlobalLock('/var/lock/launchpad-archive-cruft-check.lock')
    Lock.acquire(blocking=True)

    Log.debug("Initialising connection.")
    Ztm = initZopeless(dbuser="lucille", dbname="launchpad_prod",
                       dbhost="jubany")

    execute_zcml_for_scripts()

    bpr = getUtility(IBinaryPackageReleaseSet)

    return args

################################################################################

def cruft_check(distrorelease):
    global source_binaries, source_versions
    
    nbs = {}
    asba = {}

    bin_pkgs = {}
    source_binaries = {}
    source_versions = {}
    arch_any = {}
    
    architectures = dict([(a.architecturetag,a) for a in distrorelease.architectures])
    components = dict([(c.name,c) for c in distrorelease.components])


    for component in components:
        # XXX de-hardcode me harder
        filename = "/srv/launchpad.net/ubuntu-archive/" + \
                    "ubuntu/dists/%s/%s/source/Sources.gz" \
                    % (distrorelease.name, component)
        # apt_pkg.ParseTagFile needs a real file handle and can't handle a GzipFile instance...
        temp_filename = dak_utils.temp_filename()
        (result, output) = commands.getstatusoutput("gunzip -c %s > %s" % (filename, temp_filename))
        if (result != 0):
            sys.stderr.write("Gunzip invocation failed!\n%s\n" % (output))
            sys.exit(result)
        sources = open(temp_filename)
        Sources = apt_pkg.ParseTagFile(sources)
        while Sources.Step():
            source = Sources.Section.Find("Package")
            source_version = Sources.Section.Find("Version")
            architecture = Sources.Section.Find("Architecture")
            binaries = Sources.Section.Find("Binary")
            binaries_list = map(string.strip, binaries.split(','))
            for binary in binaries_list:
                bin_pkgs.setdefault(binary, [])
                bin_pkgs[binary].append(source)
            source_binaries[source] = binaries
            source_versions[source] = source_version

        sources.close()
        os.unlink(temp_filename)

    components_and_di = []
    for component in components:
        components_and_di.append(component)
        components_and_di.append('%s/debian-installer' % (component))

    # Checks based on the Packages files
    for component in components_and_di:
        for architecture in architectures:
            # XXX de-hardcode me harder
            filename = "/srv/launchpad.net/ubuntu-archive/ubuntu" + \
                       "/dists/%s/%s/binary-%s/Packages.gz" \
                       % (distrorelease.name, component, architecture)
            # apt_pkg.ParseTagFile needs a real file handle
            temp_filename = dak_utils.temp_filename()
            (result, output) = commands.getstatusoutput("gunzip -c %s > %s" % (filename, temp_filename))
            if (result != 0):
                sys.stderr.write("Gunzip invocation failed!\n%s\n" % (output))
                sys.exit(result)
            packages = open(temp_filename)
            Packages = apt_pkg.ParseTagFile(packages)
            while Packages.Step():
                package = Packages.Section.Find('Package')
                source = Packages.Section.Find('Source', "")
                version = Packages.Section.Find('Version')
                architecture = Packages.Section.Find('Architecture')
                if source == "":
                    source = package
                if source.find("(") != -1:
                    m = dak_utils.re_extract_src_version.match(source)
                    source = m.group(1)
                    version = m.group(2)
                if not bin_pkgs.has_key(package):
                    nbs.setdefault(source,{})
                    nbs[source].setdefault(package, {})
                    nbs[source][package][version] = ""
                if architecture != "all":
                    arch_any.setdefault(package, "0")
                    if apt_pkg.VersionCompare(version, arch_any[package]) < 1:
                        arch_any[package] = version
            packages.close()
            os.unlink(temp_filename)

    # Checks based on the Packages files
    for component in components_and_di:
        for architecture in architectures:
            # XXX de-hardcode me harder
            filename = "/srv/launchpad.net/ubuntu-archive/ubuntu" + \
                       "/dists/%s/%s/binary-%s/Packages.gz" \
                       % (distrorelease.name, component, architecture)
            # apt_pkg.ParseTagFile needs a real file handle
            temp_filename = dak_utils.temp_filename()
            (result, output) = commands.getstatusoutput("gunzip -c %s > %s" % (filename, temp_filename))
            if (result != 0):
                sys.stderr.write("Gunzip invocation failed!\n%s\n" % (output))
                sys.exit(result)
            packages = open(temp_filename)
            Packages = apt_pkg.ParseTagFile(packages)
            while Packages.Step():
                package = Packages.Section.Find('Package')
                source = Packages.Section.Find('Source', "")
                version = Packages.Section.Find('Version')
                architecture = Packages.Section.Find('Architecture')
                if source == "":
                    source = package
                if source.find("(") != -1:
                    m = dak_utils.re_extract_src_version.match(source)
                    source = m.group(1)
                    version = m.group(2)
                if architecture == "all":
                    if arch_any.has_key(package) and \
                           apt_pkg.VersionCompare(version, arch_any[package]) > -1:
                        asba.setdefault(source,{})
                        asba[source].setdefault(package, {})
                        asba[source][package].setdefault(version, {})
                        asba[source][package][version][architecture] = ""
            packages.close()
            os.unlink(temp_filename)

    return (nbs, asba)

################################################################################

def add_nbs(nbs_d, source, version, package):
    # Ensure the package is still in the suite (someone may have already removed
    # it).
    result = bpr.getByNameInDistroRelease(Options.distrorelease, package)
    if len(list(result)) == 0:
        return

    nbs_d.setdefault(source, {})
    nbs_d[source].setdefault(version, {})
    nbs_d[source][version][package] = ""

################################################################################

def refine_nbs(nbs):
    # Distinguish dubious (version numbers match) and 'real' NBS (they don't)
    dubious_nbs = {}
    real_nbs = {}
    for source in nbs.keys():
        for package in nbs[source].keys():
            versions = nbs[source][package].keys()
            versions.sort(apt_pkg.VersionCompare)
            latest_version = versions.pop()
            source_version = source_versions.get(source, "0")
            if apt_pkg.VersionCompare(latest_version, source_version) == 0:
                add_nbs(dubious_nbs, source, latest_version, package)
            else:
                add_nbs(real_nbs, source, latest_version, package)

    return (real_nbs, dubious_nbs)

################################################################################

def output_nbs(real_nbs):
    output = "Not Built from Source\n"
    output += "---------------------\n\n"

    nbs_to_remove = []
    nbs_keys = real_nbs.keys()
    nbs_keys.sort()
    for source in nbs_keys:
        output += " * %s_%s builds: %s\n" % (source,
                                       source_versions.get(source, "??"),
                                       source_binaries.get(source, "(source does not exist)"))
        output += "      but no longer builds:\n"
        versions = real_nbs[source].keys()
        versions.sort(apt_pkg.VersionCompare)
        for version in versions:
            packages = real_nbs[source][version].keys()
            packages.sort()
            for pkg in packages:
                nbs_to_remove.append(pkg)
            output += "        o %s: %s\n" % (version, ", ".join(packages))

        output += "\n"

    if nbs_to_remove:
        print output

    return nbs_to_remove

################################################################################

def do_removals(nbs_to_remove):
    Ztm.begin()
    for package in nbs_to_remove:
        for distroarchrelease in Options.distrorelease.architectures:
            binarypackagename = getUtility(IBinaryPackageNameSet)[package]
            darbp = DistroArchReleaseBinaryPackage(distroarchrelease, binarypackagename)
            try:
                sbpph = darbp.supersede()
            # We're blindly removing for all arches, if it's not there
            # for some, that's fine ...
            except NotFoundError:
                pass
            else:
                version = sbpph.binarypackagerelease.version
                print "Removed %s_%s from %s/%s ... " % (package,
                                                         version,
                                                         Options.distrorelease.name,
                                                         distroarchrelease.architecturetag)
    Ztm.commit()

################################################################################

def main():
    init()

    if not Options.distro:
        Options.distro = "ubuntu"
    Options.distro = getUtility(IDistributionSet)[Options.distro]

    if not Options.distrorelease:
        Options.distrorelease = Options.distro.currentrelease.name
    Options.distrorelease = Options.distro.getRelease(Options.distrorelease)

    (nbs, asba) = cruft_check(Options.distrorelease)

    # XXX do something useful with asba
    for src in asba:
        for pkg in asba[src]:
            print "ASBA: %s" % pkg

    (real_nbs, _) = refine_nbs(nbs)
    nbs_to_remove = output_nbs(real_nbs)

    if nbs_to_remove:
        if Options.action:
            dak_utils.game_over()
            do_removals(nbs_to_remove)
    
    Lock.release()
    return 0

################################################################################

if __name__ == '__main__':
    sys.exit(main())
