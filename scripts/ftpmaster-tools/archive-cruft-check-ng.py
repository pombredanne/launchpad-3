#!/usr/bin/env python
# Copyright 2006 Canonical Ltd

"""Archive Cruft checker

A kind of archive garbage collector, supersede NBS binaries (not build
from source).
"""
import _pythonpath
import optparse
import sys

from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.scripts.ftpmaster import (
    ArchiveCruftChecker, ArchiveCruftChecker)
from canonical.lp import initZopeless
from contrib.glock import GlobalLock


def main():
    # Parse command-line arguments
    parser = optparse.OptionParser()

    logger_options(parser)

    parser.add_option("-d", "--distro", dest="distro",
                      help="remove from DISTRO")
    parser.add_option("-n", "--no-action", dest="action",
                      default=True, action="store_false",
                      help="don't do anything")
    parser.add_option("-s", "--suite", dest="suite",
                      help="only act on SUITE")

    (Options, args) = parser.parse_args()

    Log = logger(Options, "archive-cruft-check")

    Log.debug("Acquiring lock")
    Lock = GlobalLock('/var/lock/launchpad-archive-cruft-check.lock')
    Lock.acquire(blocking=True)

    Log.debug("Initialising connection.")
    ztm = initZopeless(dbuser="lucille")
    execute_zcml_for_scripts()


    if len(args) > 0:
        archive_path = args[0]
    else:
        archive_path = None

    checker = ArchiveCruftChecker(Log, distribution_name=Options.distro,
                                  suite=Options.suite,
                                  archive_path=archive_path)

    try:
        checker.initialize()
    except ArchiveCruftChecker, info:
        Log.error(info)
        return 1

    if checker.nbs_to_remove and Options.action:
        checker.doRemovals()
        ztm.commit()

    Lock.release()
    return 0


if __name__ == '__main__':
    sys.exit(main())
