#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Generate a file mapping ~user/product/branch to on-disk paths, suitable for
use with Apache's RewriteMap directive.

Apache config notes:

  - magic incantation::
      
      RewriteMap branch-list txt:/path/to/map-file.txt
      ...
      RewriteEngine On
      # Assume branch dirs are kept in a directory 'branches' under the
      # DocumentRoot
      RewriteRule ^(~[^/]+/[^/]+/[^/]+)/ branches/${branch-list:$1}/

  - UserDir directive must not be in effect if you want to be able to rewrite
    top-level ~user paths.
"""

__metaclass__ = type

import _pythonpath

import sys
from optparse import OptionParser

from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts import supermirror_rewritemap
from canonical.lp import initZopeless
from canonical.config import config

_default_lock_file = '/var/lock/supermirror-rewritemap.lock'

def main():
    parser = OptionParser(description=__doc__)
    logger_options(parser)

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error('expected a filename argument')
    
    filename = args[0]

    log = logger(options)

    lockfile = LockFile(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info('Lockfile %s in use', _default_lock_file)
        sys.exit(1)

    try:
        execute_zcml_for_scripts()
        ztm = initZopeless(
                dbuser=config.supermirror.dbuser, implicitBegin=False
                )
        outfile = open(filename, 'wb')
        ztm.begin()
        supermirror_rewritemap.main(outfile)
        ztm.abort()
        outfile.close()
    finally:
        lockfile.release()


if __name__ == '__main__':
    main()
