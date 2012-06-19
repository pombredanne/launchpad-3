#!/usr/bin/python -S
#
# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

from lp.bugs.scripts.bugsummaryrebuild import (
    BugSummaryRebuildTunableLoop,
    )
from lp.services.scripts.base import LaunchpadScript


class BugSummaryRebuild(LaunchpadScript):

    def main(self):
        updater = BugSummaryRebuildTunableLoop(self.logger)
        updater.run()

if __name__ == '__main__':
    script = BugSummaryRebuild('bugsummary-rebuild', dbuser='testadmin')
    script.lock_and_run()
