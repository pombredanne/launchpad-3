#!/usr/bin/env python

"""Change the component of a package.

This tool allows you to change the component of a package.  Changes won't
take affect till the next publishing run.
"""

import _pythonpath

import optparse
import sys

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
                                         logger, logger_options)
from canonical.launchpad.database import (DistroArchReleaseBinaryPackage,
                                          DistroReleaseSourcePackageRelease)
from canonical.launchpad.interfaces import (IBinaryPackageNameSet,
                                            IDistributionSet, NotFoundError)

from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingPriority)

from contrib.glock import GlobalLock

################################################################################

Options = None
Log = None
Ztm = None
Lock = None

################################################################################

def binaries_of_source(distrorelease, sourcepackage_name):
    # XXX only gets latest source package for this distrorelease, ok?
    # XXX - there is method for this in SPR....
    sp = distrorelease.getSourcePackage(sourcepackage_name)
    binaries = set()
    for release in sp.releases:
        for binary in release.sourcepackagerelease.binaries:
            binaries.add(binary.binarypackagename.name)
    return binaries

########################################

def process_source_change(distrorelease, package):
    Ztm.begin()
    (new_component, new_section) = (None, None)
    if Options.component:
        new_component = Options.component
    if Options.section:
        new_section = Options.section

    spr = distrorelease.getSourcePackage(package).releasehistory[-1]
    drspr = DistroReleaseSourcePackageRelease(distrorelease, spr)
    drspr.changeOverride(new_component=new_component, new_section=new_section)
    Ztm.commit()

########################################

def process_binary_change(distrorelease, package):
    Ztm.begin()
    (new_component, new_section, new_priority) = (None, None, None)
    if Options.component:
        new_component = Options.component
    if Options.section:
        new_section = Options.section
    if Options.priority:
        new_priority = Options.priority
    for distroarchrelease in distrorelease.architectures:
        binarypackagename = getUtility(IBinaryPackageNameSet)[package]
        darbp = DistroArchReleaseBinaryPackage(
            distroarchrelease, binarypackagename)
        try:
            darbp.changeOverride(
                new_component=new_component, new_priority=new_priority,
                new_section=new_section)
        except NotFoundError:
            pass
    Ztm.commit()

################################################################################

def init():
    global Options, Log, Ztm, Lock

    # Parse command-line arguments
    parser = optparse.OptionParser()
    logger_options(parser)
    parser.add_option("-B", "--binary-and-source", dest="binaryandsource",
                      default=False, action="store_true",
                      help="select source and binary (of the same name)")
    parser.add_option("-c", "--component", dest="component",
                      help="move package to COMPONENT")
    parser.add_option("-d", "--distro", dest="distro",
                      help="move package in DISTRO")
    parser.add_option("-n", "--no-action", dest="action", default=True,
                      action="store_false", help="don't actually do anything")
    parser.add_option("-p", "--priority", dest="priority",
                      help="move package to PRIORITY")
    parser.add_option("-s", "--suite", dest="suite",
                      help="move package in suite SUITE")
    parser.add_option("-S", "--source-and-binary", dest="sourceandchildren",
                      default=False, action="store_true",
                      help="select source and binaries with the same name")
    parser.add_option("-t", "--source-only", dest="sourceonly",
                      default=False, action="store_true",
                      help="select source packages only")
    parser.add_option("-x", "--section", dest="section",
                      help="move package to SECTION")
    
    (Options, args) = parser.parse_args()
    Log = logger(Options, "change-component")

    if len(args) < 1:
        Log.error("Need to be given the name of a package to move.")
        sys.exit(1)

    Log.debug("Acquiring lock")
    Lock = GlobalLock('/var/lock/launchpad-change-component.lock')
    Lock.acquire(blocking=True)

    Log.debug("Initialising connection.")
    Ztm = initZopeless(dbuser="lucille")

    execute_zcml_for_scripts()

    if not Options.distro:
        Options.distro = "ubuntu"
    Options.distro = getUtility(IDistributionSet)[Options.distro]

    if not Options.suite:
        Options.distrorelease = Options.distro.currentrelease
        Options.pocket = PackagePublishingPocket.RELEASE
    else:
        Options.distrorelease, Options.pocket = (
            Options.distro.getDistroReleaseAndPocket(Options.suite))

    return args

################################################################################

def validate_options():
    if not Options.component and not Options.section and not Options.priority:
        Log.error("need either a component, section or priority to change.")
        sys.exit(1)

    if Options.component:
        valid_components = dict([(c.name,c) for c in
                                 Options.distrorelease.components])

        if Options.component not in valid_components:
            Log.error("%s is not a valid component for %s/%s."
                      % (Options.component, Options.distro.name,
                         Options.distrorelease.name))
            sys.exit(1)
        Options.component = valid_components[Options.component]

    if Options.section:
        valid_sections = dict(
            [(s.name,s) for s in Options.distrorelease.sections])
        if Options.section not in valid_sections:
            Log.error("%s is not a valid section for %s/%s." 
                      % (Options.section, Options.distro.name,
                         Options.distrorelease.name))
            sys.exit(1)
        Options.section = valid_sections[Options.section]

    if Options.priority:
        valid_priorities = dict(
            [(priority.name.lower(), priority)
             for priority in PackagePublishingPriority.items])
        if Options.priority not in valid_priorities:
            Log.error("%s is not a valid priority for %s/%s."
                      % (Options.priority, Options.distro.name,
                         Options.distrorelease.name))
            sys.exit(1)
        Options.priority = valid_priorities[Options.priority]


################################################################################

def main():
    arguments = init()

    validate_options()
    
    for package in arguments:
        if (Options.sourceonly or Options.binaryandsource or
            Options.sourceandchildren):
            process_source_change(Options.distrorelease, package)

        if Options.sourceandchildren:
            for child in binaries_of_source(Options.distrorelease, package):
                process_binary_change(Options.distrorelease, child)
        elif not Options.sourceonly:
            process_binary_change(Options.distrorelease, package)

    Lock.release()
    return 0

################################################################################

if __name__ == '__main__':
    sys.exit(main())
