#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

# This script updates the cached stats in the system

import _pythonpath

from lp.services.scripts.base import LaunchpadCronScript
from lp.bugs.scripts.bugtasktargetnamecaches import (
    BugTaskTargetNameCacheUpdater)
from canonical.config import config


class UpdateBugTaskTargetNameCaches(LaunchpadCronScript):
    """Update the targetnamecache for all IBugTasks.

    This ensures that the cache values are up-to-date even after, for
    example, an IDistribution being renamed.
    """
    def main(self):
        updater = BugTaskTargetNameCacheUpdater(self.txn, self.logger)
        updater.run()

if __name__ == '__main__':
    script = UpdateBugTaskTargetNameCaches(
        'launchpad-targetnamecacheupdater',
        dbuser=config.targetnamecacheupdater.dbuser)
    script.lock_and_run()

