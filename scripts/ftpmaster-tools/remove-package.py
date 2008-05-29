#!/usr/bin/python2.4

# General purpose package removal tool for ftpmaster
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005  James Troup <james@nocrew.org>
# Copyright (C) 2006  James Troup <james.troup@canonical.com>

################################################################################

import commands
import optparse
import os
import re
import sys

import dak_utils

import apt_pkg

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database import (SecureBinaryPackagePublishingHistory,
                                          SecureSourcePackagePublishingHistory)
from canonical.launchpad.interfaces import (
    IDistributionSet, PackagePublishingStatus)
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
                                         logger, logger_options)
from canonical.lp import initZopeless

from contrib.glock import GlobalLock

################################################################################

re_strip_source_version = re.compile (r'\s+.*$')
re_build_dep_arch = re.compile(r"\[[^]]+\]")

################################################################################

Options = None
Lock = None
Log = None
ztm = None

################################################################################

def game_over():
    answer = dak_utils.our_raw_input("Continue (y/N)? ").lower()
    if answer != "y":
        print "Aborted."
        sys.exit(1)

################################################################################

# def reverse_depends_check(removals, suites):
#     print "Checking reverse dependencies..."
#     components = Cnf.ValueList("Suite::%s::Components" % suites[0])
#     dep_problem = 0
#     p2c = {}
#     for architecture in Cnf.ValueList("Suite::%s::Architectures" % suites[0]):
#         if architecture in ["source", "all"]:
#             continue
#         deps = {}
#         virtual_packages = {}
#         for component in components:
#             filename = "%s/dists/%s/%s/binary-%s/Packages.gz" \
#                        % (Cnf["Dir::Root"], suites[0], component,
#                           architecture)
#             # apt_pkg.ParseTagFile needs a real file handle and can't
#             # handle a GzipFile instance...
#             temp_filename = dak_utils.temp_filename()
#             (result, output) = commands.getstatusoutput("gunzip -c %s > %s" \
#                                                         % (filename, temp_filename))
#             if (result != 0):
#                 dak_utils.fubar("Gunzip invocation failed!\n%s\n" \
#                                 % (output), result)
#             packages = open(temp_filename)
#             Packages = apt_pkg.ParseTagFile(packages)
#             while Packages.Step():
#                 package = Packages.Section.Find("Package")
#                 depends = Packages.Section.Find("Depends")
#                 if depends:
#                     deps[package] = depends
#                 provides = Packages.Section.Find("Provides")
#                 # Maintain a counter for each virtual package.  If a
#                 # Provides: exists, set the counter to 0 and count all
#                 # provides by a package not in the list for removal.
#                 # If the counter stays 0 at the end, we know that only
#                 # the to-be-removed packages provided this virtual
#                 # package.
#                 if provides:
#                     for virtual_pkg in provides.split(","):
#                         virtual_pkg = virtual_pkg.strip()
#                         if virtual_pkg == package: continue
#                         if not virtual_packages.has_key(virtual_pkg):
#                             virtual_packages[virtual_pkg] = 0
#                         if package not in removals:
#                             virtual_packages[virtual_pkg] += 1
#                 p2c[package] = component
#             packages.close()
#             os.unlink(temp_filename)

#         # If a virtual package is only provided by the to-be-removed
#         # packages, treat the virtual package as to-be-removed too.
#         for virtual_pkg in virtual_packages.keys():
#             if virtual_packages[virtual_pkg] == 0:
#                 removals.append(virtual_pkg)

#         # Check binary dependencies (Depends)
#         for package in deps.keys():
#             if package in removals: continue
#             parsed_dep = []
#             try:
#                 parsed_dep += apt_pkg.ParseDepends(deps[package])
#             except ValueError, e:
#                 print "Error for package %s: %s" % (package, e)
#             for dep in parsed_dep:
#                 # Check for partial breakage.  If a package has a ORed
#                 # dependency, there is only a dependency problem if all
#                 # packages in the ORed depends will be removed.
#                 unsat = 0
#                 for dep_package, _, _ in dep:
#                     if dep_package in removals:
#                             unsat += 1
#                 if unsat == len(dep):
#                     component = p2c[package]
#                     if component != "main":
#                         what = "%s/%s" % (package, component)
#                     else:
#                         what = "** %s" % (package)
#                     print "%s has an unsatisfied dependency on %s: %s" \
#                           % (what, architecture, dak_utils.pp_deps(dep))
#                     dep_problem = 1

#     # Check source dependencies (Build-Depends and Build-Depends-Indep)
#     for component in components:
#         filename = "%s/dists/%s/%s/source/Sources.gz" \
#                    % (Cnf["Dir::Root"], suites[0], component)
#         # apt_pkg.ParseTagFile needs a real file handle and can't
#         # handle a GzipFile instance...
#         temp_filename = dak_utils.temp_filename()
#         result, output = commands.getstatusoutput("gunzip -c %s > %s" \
#                                                   % (filename, temp_filename))
#         if result != 0:
#             sys.stderr.write("Gunzip invocation failed!\n%s\n" \
#                              % (output))
#             sys.exit(result)
#         sources = open(temp_filename)
#         Sources = apt_pkg.ParseTagFile(sources)
#         while Sources.Step():
#             source = Sources.Section.Find("Package")
#             if source in removals: continue
#             parsed_dep = []
#             for build_dep_type in ["Build-Depends", "Build-Depends-Indep"]:
#                 build_dep = Sources.Section.get(build_dep_type)
#                 if build_dep:
#                     # Remove [arch] information since we want to see
#                     # breakage on all arches
#                     build_dep = re_build_dep_arch.sub("", build_dep)
#                     try:
#                         parsed_dep += apt_pkg.ParseDepends(build_dep)
#                     except ValueError, e:
#                         print "Error for source %s: %s" % (source, e)
#             for dep in parsed_dep:
#                 unsat = 0
#                 for dep_package, _, _ in dep:
#                     if dep_package in removals:
#                             unsat += 1
#                 if unsat == len(dep):
#                     if component != "main":
#                         source = "%s/%s" % (source, component)
#                     else:
#                         source = "** %s" % (source)
#                     print "%s has an unsatisfied build-dependency: %s" \
#                           % (source, dak_utils.pp_deps(dep))
#                     dep_problem = 1
#         sources.close()
#         os.unlink(temp_filename)

#     if dep_problem:
#         print "Dependency problem found."
#         if Options.action:
#             game_over()
#     else:
#         print "No dependency problem found."
#     print
    
################################################################################

def options_init():
    global Options
    
    parser = optparse.OptionParser()
    logger_options(parser)
    parser.add_option("-a", "--architecture", dest="architecture",
                      help="only act on ARCHITECTURE")
    parser.add_option("-b", "--binary", dest="binaryonly",
                      default=False, action="store_true",
                      help="remove binaries only")
    parser.add_option("-c", "--component", dest="component",
                      help="only act on COMPONENT")
    parser.add_option("-d", "--distro", dest="distro",
                      help="remove from DISTRO")
    parser.add_option("-m", "--reason", dest="reason",
                      help="reason for removal")
    parser.add_option("-n", "--no-action", dest="action",
                      default=True, action="store_false",
                      help="don't do anything")
    parser.add_option("-R", "--rdep-check", dest="rdepcheck",
                      default=False, action="store_true",
                      help="check reverse dependencies")
    parser.add_option("-s", "--suite", dest="suite",
                      help="only act on SUITE")
    parser.add_option("-S", "--source-only", dest="sourceonly",
                      default=False, action="store_true",
                      help="remove source only")

    (Options, arguments) = parser.parse_args()

    # Sanity check options
    if not arguments:
        dak_utils.fubar("need at least one package name as an argument.")
    if Options.architecture and Options.sourceonly:
        dak_utils.fubar("can't use -a/--architecutre and -S/"
                        "--source-only options simultaneously.")
    if Options.binaryonly and Options.sourceonly:
        dak_utils.fubar("can't use -b/--binary-only and -S/"
                        "--source-only options simultaneously.")

    if not Options.reason:
        Options.reason = ""

    # XXX malcc 2006-08-03: 'dak rm' used to check here whether or not we're
    # removing from anything other than << unstable.  This never got ported
    # to ubuntu anyway, but it might be nice someday.

    # Additional architecture checks
    # XXX James Troup 2006-01-30: parse_args.
    if Options.architecture and 0:
        dak_utils.warn("'source' in -a/--argument makes no sense and is ignored.")

    return arguments

################################################################################
def init():
    global Lock, Log, ztm

    apt_pkg.init()

    arguments = options_init()

    Log = logger(Options, "remove-package")

    Log.debug("Acquiring lock")
    Lock = GlobalLock('/var/lock/launchpad-remove-package.lock')
    Lock.acquire(blocking=True)

    Log.debug("Initialising connection.")
    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.archivepublisher.dbuser)

    if not Options.distro:
        Options.distro = "ubuntu"
    Options.distro = getUtility(IDistributionSet)[Options.distro]

    if not Options.suite:
        Options.suite = Options.distro.currentseries.name

    Options.architecture = dak_utils.split_args(Options.architecture)
    Options.component = dak_utils.split_args(Options.component)
    Options.suite = dak_utils.split_args(Options.suite)

    return arguments

################################################################################    

def summary_to_remove(to_remove):
    # Generate the summary of what's to be removed
    d = {}
    for removal in to_remove:
        package = removal["package"]
        version = removal["version"]
        architecture = removal["architecture"]
        if not d.has_key(package):
            d[package] = {}
        if not d[package].has_key(version):
            d[package][version] = []
        if architecture not in d[package][version]:
            d[package][version].append(architecture)

    summary = ""
    removals = d.keys()
    removals.sort()
    for package in removals:
        versions = d[package].keys()
        versions.sort(apt_pkg.VersionCompare)
        for version in versions:
            d[package][version].sort(dak_utils.arch_compare_sw)
            summary += "%10s | %10s | %s\n" % (package, version,
                                               ", ".join(d[package][version]))

    suites_list = dak_utils.join_with_commas_and(Options.suite);
    print "Will remove the following packages from %s:" % (suites_list)
    print
    print summary
    print
    print "------------------- Reason -------------------"
    print Options.reason
    print "----------------------------------------------"
    print

    return summary

################################################################################   

def what_to_remove(packages):
    to_remove = []

    # We have 3 modes of package selection: binary-only, source-only
    # and source+binary.  The first two are trivial and obvious; the
    # latter is a nasty mess, but very nice from a UI perspective so
    # we try to support it.

    for removal in packages:
        for suite in Options.suite:
            distro_series = Options.distro.getSeries(suite)

            if Options.sourceonly:
                bpp_list = []
            else:
                if Options.binaryonly:
                    bpp_list = distro_series.getBinaryPackagePublishing(removal)
                else:
                    bpp_list = distro_series.getBinaryPackagePublishing(
                        sourcename=removal)

            for bpp in bpp_list:
                package=bpp.binarypackagerelease.binarypackagename.name
                version=bpp.binarypackagerelease.version
                architecture=bpp.distroarchseries.architecturetag
                if (Options.architecture and
                    architecture not in Options.architecture):
                    continue
                if (Options.component and
                    bpp.component.name not in Options.component):
                    continue
                d = dak_utils.Dict(
                    type="binary", publishing=bpp, package=package,
                    version=version, architecture=architecture)
                to_remove.append(d)

            if not Options.binaryonly:
                for spp in distro_series.getPublishedReleases(removal):
                    package = spp.sourcepackagerelease.sourcepackagename.name
                    version = spp.sourcepackagerelease.version
                    if (Options.component and
                        spp.component.name not in Options.component):
                        continue
                    d = dak_utils.Dict(
                        type="source",publishing=spp, package=package,
                        version=version, architecture="source")
                    to_remove.append(d)

    return to_remove

################################################################################

def do_removal(removal):
    """Perform published package removal.

    Mark provided publishing record as SUPERSEDED, such that the Domination
    procedure will sort out its eventual removal appropriately; obeying the
    rules for archive consistency.
    """
    current = removal["publishing"]
    if removal["type"] == "binary":
        real_current = SecureBinaryPackagePublishingHistory.get(current.id)
    else:
        real_current = SecureSourcePackagePublishingHistory.get(current.id)
    real_current.status = PackagePublishingStatus.SUPERSEDED
    real_current.datesuperseded = UTC_NOW

################################################################################

def main ():
    packages = init()

    print "Working...",
    sys.stdout.flush()
    to_remove = what_to_remove(packages)
    print "done."

    if not to_remove:
        print "Nothing to do."
        sys.exit(0)

    # If we don't have a reason; spawn an editor so the user can add one
    # Write the rejection email out as the <foo>.reason file
    if not Options.reason and Options.action:
        temp_filename = dak_utils.temp_filename()
        editor = os.environ.get("EDITOR","vi")
        result = os.system("%s %s" % (editor, temp_filename))
        if result != 0:
            dak_utils.fubar ("vi invocation failed for `%s'!" % (temp_filename),
                             result)
        temp_file = open(temp_filename)
        for line in temp_file.readlines():
            Options.reason += line
        temp_file.close()
        os.unlink(temp_filename)

    summary = summary_to_remove(to_remove)

    if Options.rdepcheck:
        dak_utils.fubar("Unimplemented, sucks to be you.")
        #reverse_depends_check(removals, suites)

    # If -n/--no-action, drop out here
    if not Options.action:
        sys.exit(0)

    print "Going to remove the packages now."
    game_over()

    whoami = dak_utils.whoami()
    date = commands.getoutput('date -R')
    suites_list = dak_utils.join_with_commas_and(Options.suite);

    # Log first; if it all falls apart I want a record that we at least tried.
    # XXX malcc 2006-08-03: de-hardcode me harder
    logfile = open("/srv/launchpad.net/dak/removals.txt", 'a')
    logfile.write("==================================="
                  "======================================\n")
    logfile.write("[Date: %s] [ftpmaster: %s]\n" % (date, whoami))
    logfile.write("Removed the following packages from %s:\n\n%s"
                  % (suites_list, summary))
    logfile.write("\n------------------- Reason -------------------\n%s\n"
                  % (Options.reason))
    logfile.write("----------------------------------------------\n")
    logfile.flush()

    # Do the actual deletion
    print "Deleting...",
    ztm.begin()
    for removal in to_remove:
        do_removal(removal)
    print "done."
    ztm.commit()

    logfile.write("==================================="
                  "======================================\n")
    logfile.close()

################################################################################

if __name__ == '__main__':
    main()
