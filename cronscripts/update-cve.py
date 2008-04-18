#!/usr/bin/python2.4

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""A cron script that fetches the latest database of CVE details and ensures
that all of the known CVE's are fully registered in Launchpad."""

__metaclass__ = type

import urllib2
import gzip
import StringIO
import timing
import _pythonpath

import cElementTree

from zope.interface import implements

from canonical.config import config
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.scripts.cveimport import CVEDB_NS, update_one_cve
from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)
from canonical.launchpad.utilities.looptuner import LoopTuner


class CveUpdaterTunableLoop(object):
    """An `ITunableLoop` for updating CVEs."""

    implements(ITunableLoop)

    total_updated = 0

    def __init__(self, cves, transaction, logger, offset=0):
        self.cves = cves
        self.transaction = transaction
        self.logger = logger
        self.offset = offset
        self.total_updated = 0

    def isDone(self):
        """See `ITunableLoop`."""
        return self.offset is None

    def __call__(self, chunk_size):
        """Retrieve a batch of CVEs and update them.

        See `ITunableLoop`.
        """
        chunk_size = int(chunk_size)

        self.logger.debug("More %d" % chunk_size)

        start = self.offset
        end = self.offset + chunk_size

        self.transaction.begin()

        cve_batch = self.cves[start:end]
        self.offset = None
        for cve in cve_batch:
            start += 1
            self.offset = start
            update_one_cve(cve, self.logger)
            self.total_updated += 1

        self.logger.debug("Committing.")
        self.transaction.commit()


class CVEUpdater(LaunchpadCronScript):

    def add_my_options(self):
        """Parse command line arguments."""
        self.parser.add_option(
            "-f", "--cvefile", dest="cvefile", default=None,
            help="An XML file containing the CVE database.")
        self.parser.add_option(
            "-u", "--cveurl", dest="cveurl",
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
            cve_db = gzip.GzipFile(
                fileobj=StringIO.StringIO(cve_db_gz)).read()
        else:
            raise LaunchpadScriptFailure('No CVE database file or URL given.')

        # start analysing the data
        timing.start()
        self.logger.info("Processing CVE XML...")
        dom = cElementTree.fromstring(cve_db)
        items = dom.findall(CVEDB_NS + 'item')
        self.logger.info("Updating database...")

        # We use Looptuner to control the ideal number of CVEs
        # processed in each transaction, during at least 2 seconds.
        loop = CveUpdaterTunableLoop(items, self.txn, self.logger)
        loop_tuner = LoopTuner(loop, 2)
        loop_tuner.run()

        timing.finish()
        self.logger.info('%d seconds to update database.' % timing.seconds())


if __name__ == '__main__':
    script = CVEUpdater("updatecve", config.cveupdater.dbuser)
    script.lock_and_run()

