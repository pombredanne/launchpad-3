#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Generate a file mapping ~user/product/branch to on-disk paths, suitable for
use with Apache's RewriteMap directive.

Apache config notes:

  - magic incantation::
      
      RewriteMap branch-list txt:/path/to/map-file.txt
      ...
      RewriteEngine On
      # Assume branch dirs are kept in a directory 'branches' under the
      # DocumentRoot
      RewriteRule ^/(~[^/]+/[^/]+/[^/]+)/(.*)$ branches/${branch-list:$1}/$2 [L]

  - UserDir directive must not be in effect if you want to be able to rewrite
    top-level ~user paths.
"""

__metaclass__ = type

import _pythonpath

import sys
from optparse import OptionParser
import logging

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.scripts import supermirror_rewritemap
from canonical.lp import initZopeless
from canonical.config import config

_default_lock_file = '/var/lock/supermirror-rewritemap.lock'

def main():
    parser = OptionParser(description=__doc__)
    logger_options(parser, default=logging.WARNING)

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error('expected a filename argument')
    
    filename = args[0]

    log = logger(options)

    lockfile = GlobalLock(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except LockAlreadyAcquired:
        log.error('Lockfile %s in use', _default_lock_file)
        sys.exit(1)

    try:
        execute_zcml_for_scripts()
        ztm = initZopeless(
                dbuser=config.supermirror.dbuser, implicitBegin=False
                )
        ztm.begin()
        outfile = open(filename, 'wb')
        supermirror_rewritemap.write_map(outfile)
        outfile.close()
        ztm.abort()
    finally:
        lockfile.release()


if __name__ == '__main__':
    main()
