#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""Refresh and verify cached POFile translation statistics."""

import _pythonpath

from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.verify_pofile_stats import (
    VerifyPOFileStatsProcess)


class VerifyPOFileStats(LaunchpadCronScript):
    """Trawl `POFile` table, verifying and updating cached statistics."""

    def main(self):
        VerifyPOFileStatsProcess(self.txn, self.logger).run()


if __name__ == '__main__':
    script = VerifyPOFileStats(name="pofile-stats", dbuser='pofilestats')
    script.lock_and_run()

