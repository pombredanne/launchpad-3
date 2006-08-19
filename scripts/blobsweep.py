#!/usr/bin/env python
"""BLOB Sweeper

We accept temporary BLOB's for storage in the TemporaryBlobStorage table.
These are held for a short period, and then deleted. This script is
responsible for deleting all the BLOBs that are older than a preset
threshold.
"""

import _pythonpath

import os
import sys
from optparse import OptionParser

from zope.component import getUtility

from canonical.lp import initZopeless
from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)

from canonical.launchpad.interfaces import ITemporaryStorageManager

def main():
    options = readOptions()
    log = logger(options, "blobsweep")
    log.debug("Initialising connection.")
    ztm = initZopeless(dbuser=config.blobsweeper.dbuser)
    execute_zcml_for_scripts()
    tsm = getUtility(ITemporaryStorageManager)
    age = config.blobsweeper.max_allowed_blob_age
    if options.age is not None:
        age = options.age
    print 'Cutoff is %d seconds.' % age
    swept = tsm.sweep(age)
    if not options.dryrun:
        # this is for real
        ztm.commit()
    else:
        # this is just a test
        print 'NOTE: dry run requested, not actually deleting any blobs.'
    print '%d expired blobs deleted.' % swept
    return 0


def readOptions():
    """Read the command-line options and return an options object."""
    parser = OptionParser()
    logger_options(parser)

    parser.add_option("-N", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help=("Whether to treat this as a dry-run or not. "))

    parser.add_option("-A", "--age", action="store", type="int",
                      dest="age", metavar="SECONDS",
                      help=("The age in seconds over which blobs must be "
                            "deleted."))
    
    (options, args) = parser.parse_args()
    
    return options


if __name__ == '__main__':
    sys.exit(main())

