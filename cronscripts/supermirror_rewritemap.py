#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Generate a file mapping ~user/product/branch to on-disk paths, suitable for
use with Apache's RewriteMap directive.
"""

__metaclass__ = type

import _pythonpath

import sys
from optparse import OptionParser

from canonical.launchpad.scripts import logger_options, logger
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts import supermirror_rewritemap
from canonical.lp import initZopeless
from canonical.config import config

_default_lock_file = '/var/lock/supermirror-rewritemap.lock'

def main():
    parser = OptionParser(description=__doc__)
    logger_options(parser)

#    parser.add_option(
#            '', "--skip-duplicates", action="store_true", default=False,
#            dest="skip_duplicates",
#            help="Skip duplicate LibraryFileContent merging"
#            )

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error('expected a filename argument')
    
    filename = args[0]

    log = logger(options)
#    librariangc.log = log

    lockfile = LockFile(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info('Lockfile %s in use', _default_lock_file)
        sys.exit(1)

    try:
        ztm = initZopeless(
                #dbuser=config.supermirror.rewritemap.dbuser, implicitBegin=False
                dbuser=config.supermirror.dbuser, implicitBegin=False
                )
        #if not options.skip_duplicates:
        #    librariangc.merge_duplicates(ztm)
        outfile = open(filename, 'wb')
        supermirror_rewritemap.main(ztm, outfile)
        outfile.close()
    finally:
        lockfile.release()


if __name__ == '__main__':
    main()
