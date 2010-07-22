#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403
"""Upstream Product Release Finder.

Scan FTP and HTTP sites specified for each ProductSeries in the database
to identify files and create new ProductRelease records for them.
"""

import _pythonpath

from canonical.config import config
from lp.services.scripts.base import LaunchpadCronScript
from lp.registry.scripts.productreleasefinder.finder import (
    ProductReleaseFinder)


class ReleaseFinderScript(LaunchpadCronScript):
    def main(self):
        prf = ProductReleaseFinder(self.txn, self.logger)
        prf.findReleases()

if __name__ == "__main__":
    script = ReleaseFinderScript('productreleasefinder',
        dbuser=config.productreleasefinder.dbuser)
    script.lock_and_run()

