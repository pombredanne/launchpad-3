#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

# This script updates the cached stats in the system

import _pythonpath

from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.bugtasktargetnamecaches import (
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
    script.lock_and_run(implicit_begin=False)

