#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

# This script updates the cached stats in the system

import _pythonpath

from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.bugtasktargetnamecaches import (
    BugTaskTargetNameCachesTunableLoop)
from canonical.launchpad.utilities.looptuner import LoopTuner
from canonical.config import config


class UpdateBugTaskTargetNameCaches(LaunchpadCronScript):
    """Update the targetnamecache for all IBugTasks.

    This ensures that the cache values are up-to-date even after, for
    example, an IDistribution being renamed.
    """
    def main(self):
        self.logger.info("Updating targetname cache of bugtasks.")
        loop = BugTaskTargetNameCachesTunableLoop(self.txn, self.logger)

        loop_tuner = LoopTuner(loop, 1)
        loop_tuner.run()

        self.logger.info("Finished updating targetname cache of bugtasks.")


if __name__ == '__main__':
    script = UpdateBugTaskTargetNameCaches('launchpad-targetnamecacheupdater', 
        dbuser=config.targetnamecacheupdater.dbuser)
    script.lock_and_run(implicit_begin=False)

