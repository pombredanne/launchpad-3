#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Refresh and verify cached statistics for recently touched POFiles."""

import _pythonpath

from lp.services.scripts.base import LaunchpadCronScript
from lp.translations.scripts.verify_pofile_stats import (
    VerifyRecentPOFileStatsProcess)


class VerifyRecentPOFileStats(LaunchpadCronScript):
    """Go through recently touched `POFile`s and update their statistics."""

    def main(self):
        verifier = VerifyRecentPOFileStatsProcess(self.txn, self.logger)
        verifier.run()


if __name__ == '__main__':
    script = VerifyRecentPOFileStats(name="pofile-stats-daily",
                                     dbuser='pofilestats_daily')
    script.lock_and_run()
