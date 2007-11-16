#!/usr/bin/python2.4
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""Librarian garbage collector.

This script is run on the Librarian server to merge duplicate files,
remove expired files from the file system and clean up unreachable
rows in the database.
"""

__metaclass__ = type

import _pythonpath
import logging

from canonical.librarian import librariangc
from canonical.database.sqlbase import AUTOCOMMIT_ISOLATION
from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript


class LibrarianGC(LaunchpadCronScript):
    def add_my_options(self):
        self.parser.add_option(
                '', "--skip-duplicates", action="store_true", default=False,
                dest="skip_duplicates",
                help="Skip duplicate LibraryFileContent merging"
                )
        self.parser.add_option(
                '', "--skip-aliases", action="store_true", default=False,
                dest="skip_aliases",
                help="Skip unreferenced LibraryFileAlias removal"
                )
        self.parser.add_option(
                '', "--skip-content", action="store_true", default=False,
                dest="skip_content",
                help="Skip unreferenced LibraryFileContent removal"
                )
        self.parser.add_option(
                '', "--skip-blobs", action="store_true", default=False,
                dest="skip_blobs",
                help="Skip removing expired TemporaryBlobStorage rows"
                )
        self.parser.add_option(
                '', "--skip-files", action="store_true", default=False,
                dest="skip_files",
                help="Skip removing files on disk with no database references"
                )

    def main(self):
        librariangc.log = self.logger

        if self.options.loglevel <= logging.DEBUG:
            librariangc.debug = True

        self.txn.set_isolation_level(AUTOCOMMIT_ISOLATION)
        conn = self.txn.conn()

        # Refuse to run if we have significant clock skew between the
        # librarian and the database.
        librariangc.confirm_no_clock_skew(conn)

        # Note that each of these next steps will issue commit commands
        # as appropriate to make this script transaction friendly
        if not self.options.skip_content:
            librariangc.delete_unreferenced_content(conn) # first sweep
        if not self.options.skip_blobs:
            librariangc.delete_expired_blobs(conn)
        if not self.options.skip_duplicates:
            librariangc.merge_duplicates(conn)
        if not self.options.skip_aliases:
            librariangc.delete_unreferenced_aliases(conn)
        if not self.options.skip_content:
            librariangc.delete_unreferenced_content(conn) # second sweep
        if not self.options.skip_files:
            librariangc.delete_unwanted_files(conn)


if __name__ == '__main__':
    script = LibrarianGC('librarian-gc',
                         dbuser=config.librarian.gc.dbuser)
    script.lock_and_run()

