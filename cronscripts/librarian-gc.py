#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Librarian garbage collector.

This script is run on the Librarian server to merge duplicate files,
remove expired files from the file system and clean up unreachable
rows in the database.
"""

__metaclass__ = type

import _pythonpath

import sys, logging
from optparse import OptionParser

from canonical.launchpad.scripts import logger_options, logger
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.librarian import librariangc
from canonical.database.sqlbase import connect, AUTOCOMMIT_ISOLATION
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
    parser.add_option(
            '', "--skip-blobs", action="store_true", default=False,
            dest="skip_blobs",
            help="Skip removing expired TemporaryBlobStorage rows"
            )
    parser.add_option(
            '', "--skip-files", action="store_true", default=False,
            dest="skip_files",
            help="Skip removing files on disk with no database references"
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

    if options.loglevel <= logging.DEBUG:
        librariangc.debug = True

    try:
        con = connect(config.librarian.gc.dbuser)
        con.set_isolation_level(AUTOCOMMIT_ISOLATION)

        # Refuse to run if we have significant clock skew between the
        # librarian and the database.
        librariangc.confirm_no_clock_skew(con)

        # Note that each of these next steps will issue commit commands
        # as appropriate to make this script transaction friendly
        if not options.skip_content:
            librariangc.delete_unreferenced_content(con) # first sweep
        if not options.skip_blobs:
            librariangc.delete_expired_blobs(con)
        if not options.skip_duplicates:
            librariangc.merge_duplicates(con)
        if not options.skip_aliases:
            librariangc.delete_unreferenced_aliases(con)
        if not options.skip_content:
            librariangc.delete_unreferenced_content(con) # second sweep
        if not options.skip_files:
            librariangc.delete_unwanted_files(con)
    finally:
        lockfile.release()


if __name__ == '__main__':
    main()
