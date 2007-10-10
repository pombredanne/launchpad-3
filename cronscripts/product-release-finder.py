#!/usr/bin/python2.4
# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
"""Upstream Product Release Finder.

Scan FTP and HTTP sites specified for each ProductSeries in the database
to identify files and create new ProductRelease records for them.
"""

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.productreleasefinder.finder import (
    ProductReleaseFinder)


class ReleaseFinderScript(LaunchpadCronScript):
    def main(self):
        prf = ProductReleaseFinder(self.txn, self.logger)
        prf.findReleases()

if __name__ == "__main__":
    script = ReleaseFinderScript('productreleasefinder',
        dbuser=config.productreleasefinder.dbuser)
    script.lock_and_run()

