#!/usr/bin/python -S
#
# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Move files from Librarian disk storage into Swift."""

__metaclass__ = type

import _pythonpath

import os

from lp.services.scripts.base import LaunchpadCronScript
from lp.services.librarianserver import swift


class LibrarianFeedSwift(LaunchpadCronScript):
    def add_my_options(self):
        self.parser.add_option(
            "-i", "--id", action="append", dest="ids", default=[],
            metavar="CONTENT_ID", help="Migrate a single file")
        self.parser.add_option(
            "-r", "--remove", action="store_true", default=False,
            help="Remove files from disk after migration (default: False)")
        self.parser.add_option(
            "-s", "--start", action="store", type=int, default=None,
            dest="start", metavar="CONTENT_ID",
            help="Migrate files starting from CONTENT_ID")
        self.parser.add_option(
            "-e", "--end", action="store", type=int, default=None,
            dest="end", metavar="CONTENT_ID",
            help="Migrate files up to and including CONTENT_ID")

    def main(self):
        if self.options.ids and (self.options.start or self.options.end):
            self.parser.error(
                "Cannot specify both individual file(s) and range")
        elif self.options.ids:
            for lfc in self.options.ids:
                swift.to_swift(self.logger, lfc, lfc, self.options.remove)
        else:
            swift.to_swift(
                self.logger, self.options.start, self.options.end,
                self.options.remove)


if __name__ == '__main__':
    # Ensure that our connections to Swift are direct, and not going via
    # a web proxy that would likely block us in any case.
    if 'http_proxy' in os.environ:
        del os.environ['http_proxy']
    if 'HTTP_PROXY' in os.environ:
        del os.environ['HTTP_PROXY']
    script = LibrarianFeedSwift(
        'librarian-feed-swift', dbuser='librarianfeedswift')
    script.lock_and_run(isolation='autocommit')
