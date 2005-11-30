#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Librarian garbage collector.

This script is run on the Librarian server to merge duplicate files,
remove expired files from the file system and clean up unreachable
rows in the database.
"""

__metaclass__ = type

import _pythonpath

import sys
from optparse import OptionParser

from canonical.launchpad.scripts import logger_options, logger
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.librarian import librariangc
from canonical.lp import initZopeless
from canonical.config import config

_default_lock_file = '/var/lock/librarian-gc.lock'

def main():
    parser = OptionParser(description=__doc__)
    logger_options(parser)

    parser.add_option(
            '', "--skip-duplicates", action="store_true", default=False,
            dest="skip_duplicates",
            help="Skip duplicate LibraryFileContent merging"
            )
    parser.add_option(
            '', "--skip-aliases", action="store_true", default=False,
            dest="skip_aliases",
            help="Skip unreferenced LibraryFileAlias removal"
            )
    parser.add_option(
            '', "--skip-content", action="store_true", default=False,
            dest="skip_content",
            help="Skip unreferenced LibraryFileContent removal"
            )

    (options, args) = parser.parse_args()

    log = logger(options)
    librariangc.log = log

    lockfile = LockFile(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info('Lockfile %s in use', _default_lock_file)
        sys.exit(1)

    try:
        ztm = initZopeless(
                dbuser=config.librarian.gc.dbuser, implicitBegin=False
                )
        # Note - no need to issue ztm.begin() or ztm.commit(),
        # as each of these next steps will issue these as appropriate
        # to make this script as transaction friendly as possible.
        if not options.skip_duplicates:
            librariangc.merge_duplicates(ztm)
        if not options.skip_aliases:
            librariangc.delete_unreferenced_aliases(ztm)
        if not options.skip_content:
            librariangc.delete_unreferenced_content(ztm)
    finally:
        lockfile.release()


if __name__ == '__main__':
    main()
