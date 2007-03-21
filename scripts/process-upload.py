#!/usr/bin/python2.4
"""Upload processor.

Given a bunch of context information and a bunch of files, process them as
an upload to a distro/whatever within the launchpad.
"""

import _pythonpath

import os
import sys
from optparse import OptionParser

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.archivepublisher.uploadpolicy import policy_options
from canonical.archivepublisher.uploadprocessor import UploadProcessor
from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.lp import initZopeless


_default_lockfile = '/var/lock/process-upload.lock'


def main():
    options = readOptions()
    log = logger(options, "process-upload")

    locker = GlobalLock(_default_lockfile, logger=log)
    try:
        locker.acquire()
    except LockAlreadyAcquired:
        log.error("Cannot acquire lock.")
        return 1

    log.debug("Initialising connection.")
    ztm = initZopeless(dbuser=config.uploader.dbuser)
    execute_zcml_for_scripts()

    try:
        UploadProcessor(options, ztm, log).processUploadQueue()
    finally:
        locker.release()

    return 0


def readOptions():
    """Read the command-line options and return an options object."""
    parser = OptionParser()
    logger_options(parser)
    policy_options(parser)

    parser.add_option("-N", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help=("Whether to treat this as a dry-run or not. "
                            "Implicitly set -KM."))

    parser.add_option("-K", "--keep", action="store_true",
                      dest="keep", metavar="KEEP", default=False,
                      help="Whether to keep or not the uploads directory.")

    parser.add_option("-M", "--no-mails", action="store_true",
                      dest="nomails", default=False,
                      help="Whether to suppress the sending of mails or not.")

    parser.add_option("-J", "--just-leaf", action="store", dest="leafname",
                      default=None, help="A specific leaf dir to limit to.",
                      metavar = "LEAF")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        raise ValueError("Need to be given exactly one non-option "
                         "argument, namely the fsroot for the upload.")
    options.base_fsroot = os.path.abspath(args[0])

    if not os.path.isdir(options.base_fsroot):
        raise ValueError("%s is not a directory" % options.base_fsroot)

    return options


if __name__ == '__main__':
    sys.exit(main())
