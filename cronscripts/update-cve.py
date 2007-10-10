#!/usr/bin/python2.4

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""A cron script that fetches the latest database of CVE details and ensures
that all of the known CVE's are fully registered in Launchpad."""

__metaclass__ = type

import urllib2
import gzip
import StringIO
import timing
import _pythonpath

import cElementTree

from canonical.config import config
from canonical.launchpad.scripts.cveimport import CVEDB_NS, update_one_cve

from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)


class CVEUpdater(LaunchpadCronScript):
    def add_my_options(self):
        """Parse command line arguments."""
        self.parser.add_option("-f", "--cvefile", dest="cvefile",
                               default=None,
                               help="An XML file containing the CVE database.")
        self.parser.add_option("-u", "--cveurl", dest="cveurl",
                               default=config.cveupdater.cve_db_url,
                               help="The URL for the gzipped XML CVE database.")

    def main(self):
        self.logger.info('Initializing...')
        if self.options.cvefile is not None:
            try:
                cve_db = open(self.options.cvefile, 'r').read()
            except IOError:
                raise LaunchpadScriptFailure(
                    'Unable to open CVE database in %s'
                    % self.options.cvefile)

        elif self.options.cveurl is not None:
            self.logger.info("Downloading CVE database from %s..." %
                             self.options.cveurl)
            try:
                url = urllib2.urlopen(self.options.cveurl)
            except (urllib2.HTTPError, urllib2.URLError), val:
                raise LaunchpadScriptFailure(
                    'Unable to connect for CVE database %s'
                    % self.options.cveurl)

            cve_db_gz = url.read()
            self.logger.info("%d bytes downloaded." % len(cve_db_gz))
            cve_db = gzip.GzipFile(fileobj=StringIO.StringIO(cve_db_gz)).read()
        else:
            raise LaunchpadScriptFailure('No CVE database file or URL given.')

        # start analysing the data
        timing.start()
        self.logger.info("Processing CVE XML...")
        dom = cElementTree.fromstring(cve_db)
        items = dom.findall(CVEDB_NS + 'item')
        self.logger.info("Updating database...")
        for item in items:
            self.txn.begin()
            update_one_cve(item, self.logger)
            self.txn.commit()
        timing.finish()
        self.logger.info('%d seconds to update database.' % timing.seconds())


if __name__ == '__main__':
    script = CVEUpdater("updatecve", config.cveupdater.dbuser)
    script.lock_and_run()

