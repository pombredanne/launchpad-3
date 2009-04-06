#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Parse librarian apache logs to find out download counts for each file."""

__metaclass__ = type

import os

# pylint: disable-msg=W0403
import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.country import ICountrySet
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.librarian_apache_log_parser import (
    create_or_update_parsedlog_entry, DBUSER, get_files_to_parse, parse_file)


class ParseLibrarianApacheLogs(LaunchpadCronScript):

    def main(self):
        root = config.librarianlogparser.logs_root
        files_to_parse = get_files_to_parse(root, os.listdir(root))

        libraryfilealias_set = getUtility(ILibraryFileAliasSet)
        country_set = getUtility(ICountrySet)
        for fd, position in files_to_parse.items():
            downloads, parsed_bytes = parse_file(fd, position)
            for file_id, daily_downloads in downloads.items():
                lfa = libraryfilealias_set[file_id]
                for day, country_downloads in daily_downloads.items():
                    for country_code, count in country_downloads.items():
                        country = country_set[country_code]
                        lfa.updateDownloadCount(day, country, count)
            fd.seek(0)
            first_line = fd.readline()
            fd.close()
            create_or_update_parsedlog_entry(first_line, parsed_bytes)
            self.txn.commit()
            self.logger.info('Finished parsing %s' % fd.name)

        self.logger.info('Done parsing apache log files for librarian')


if __name__ == '__main__':
    script = ParseLibrarianApacheLogs('parse-librarian-apache-logs', DBUSER)
    script.lock_and_run()
