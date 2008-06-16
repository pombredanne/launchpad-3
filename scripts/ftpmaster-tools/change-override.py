#!/usr/bin/python2.4

"""Change the component of a package.

This tool allows you to change the component of a package.  Changes won't
take affect till the next publishing run.
"""
import _pythonpath

import optparse
import sys

from contrib.glock import GlobalLock

from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.scripts.ftpmaster import (
    ArchiveOverrider, ArchiveOverriderError)
from canonical.lp import initZopeless


def main():
    parser = optparse.OptionParser()

    logger_options(parser)

    # transaction options
    parser.add_option("-N", "--dry-run", dest="dry_run", default=False,
                      action="store_true", help="don't actually do anything")
    # muttable fields
    parser.add_option("-d", "--distro", dest="distro_name", default='ubuntu',
                      help="move package in DISTRO")
    parser.add_option("-s", "--suite", dest="suite",
                      help="move package in suite SUITE")
    parser.add_option("-c", "--component", dest="component_name",
                      help="move package to COMPONENT")
    parser.add_option("-p", "--priority", dest="priority_name",
                      help="move package to PRIORITY")
    parser.add_option("-x", "--section", dest="section_name",
                      help="move package to SECTION")
    # control options
    parser.add_option("-S", "--source-and-binary", dest="sourceandchildren",
                      default=False, action="store_true",
                      help="select source and all binaries from this source")
    parser.add_option("-B", "--binary-and-source", dest="binaryandsource",
                      default=False, action="store_true",
                      help="select source and binary (of the same name)")
    parser.add_option("-t", "--source-only", dest="sourceonly",
                      default=False, action="store_true",
                      help="select source packages only")

    (options, args) = parser.parse_args()

    log = logger(options, "change-override")

    if len(args) < 1:
        log.error("Need to be given the name of a package to move.")
        return 1

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/launchpad-change-component.lock')
    lock.acquire(blocking=True)

    log.debug("Initialising connection.")
    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.archivepublisher.dbuser)

    # instatiate and initialize changer object
    changer = ArchiveOverrider(log, distro_name=options.distro_name,
                               suite=options.suite,
                               component_name=options.component_name,
                               section_name=options.section_name,
                               priority_name=options.priority_name)

    try:
        changer.initialize()
    except ArchiveOverriderError, info:
        log.error(info)
        return 1

    for package_name in args:
        # change matching source
        if (options.sourceonly or options.binaryandsource or
            options.sourceandchildren):
            changer.processSourceChange(package_name)
        # change all binaries for matching source
        if options.sourceandchildren:
            changer.processChildrenChange(package_name)
        # change only binary matching name
        elif not options.sourceonly:
            changer.processBinaryChange(package_name)

    if options.dry_run:
        log.info("Dry run, aborting transaction")
        ztm.abort()
    else:
        log.info("Commiting transaction, changes will be visible after "
                 "next publisher run.")
        ztm.commit()

    lock.release()
    return 0


if __name__ == '__main__':
    sys.exit(main())
