#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Parse librarian apache logs to find out download counts for each file.

Thanks to the *huge* number of different LibraryFileAlias objects this script
will fetch when parsing multiple log files from scratch and the fact that we
overwrite storm's cache with something that caches *everything*, this script
may end up eating all your RAM. That shouldn't happen in general as we run
it multiple times a day, but if we ever fail to run it for more than a week,
we may need to add a hack (store._cache.clear()) to clear the cache after
updating the counts of every LFA, in order to get through the backlog.
"""

__metaclass__ = type

import os

# pylint: disable-msg=W0403
import _pythonpath

from zope.component import getUtility

from storm.sqlobject import SQLObjectNotFound

from canonical.config import config
from canonical.launchpad.interfaces.country import ICountrySet
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.librarian_apache_log_parser import (
    create_or_update_parsedlog_entry, DBUSER, get_files_to_parse, parse_file)
from canonical.launchpad.webapp.interfaces import NotFoundError


class ParseLibrarianApacheLogs(LaunchpadCronScript):

    def main(self):
        root = config.librarianlogparser.logs_root
        files_to_parse = get_files_to_parse(root, os.listdir(root))

        libraryfilealias_set = getUtility(ILibraryFileAliasSet)
        country_set = getUtility(ICountrySet)
        for fd, position in files_to_parse.items():
            downloads, parsed_bytes = parse_file(fd, position, self.logger)
            # Use a while loop here because we want to pop items from the dict
            # in order to free some memory as we go along. This is a good
            # thing here because the downloads dict may get really huge.
            while downloads:
                file_id, daily_downloads = downloads.popitem()
                try:
                    lfa = libraryfilealias_set[file_id]
                except SQLObjectNotFound:
                    # This file has been deleted from the librarian, so don't
                    # try to store download counters for it.
                    continue
                for day, country_downloads in daily_downloads.items():
                    for country_code, count in country_downloads.items():
                        try:
                            country = country_set[country_code]
                        except NotFoundError:
                            # We don't know the country for the IP address
                            # where this request originated.
                            country = None
                        lfa.updateDownloadCount(day, country, count)
            fd.seek(0)
            first_line = fd.readline()
            fd.close()
            create_or_update_parsedlog_entry(first_line, parsed_bytes)
            self.txn.commit()
            self.logger.info('Finished parsing %s' % fd)

        self.logger.info('Done parsing apache log files for librarian')


if __name__ == '__main__':
    script = ParseLibrarianApacheLogs('parse-librarian-apache-logs', DBUSER)
    script.lock_and_run()
