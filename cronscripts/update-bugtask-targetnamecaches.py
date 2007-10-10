#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

# This script updates the cached stats in the system

import _pythonpath

from zope.component import getUtility

from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.interfaces import IBugTaskSet
from canonical.config import config


class UpdateBugTaskTargetNameCaches(LaunchpadCronScript):
    """Update the targetnamecache for all IBugTasks.

    This ensures that the cache values are up-to-date even after, for
    example, an IDistribution being renamed.
    """
    def main(self):
        self.logger.info("Updating targetname cache of bugtasks.")
        bugtaskset = getUtility(IBugTaskSet)
        self.txn.begin()
        # XXX: kiko 2006-03-23:
        # We use a special API here, which is kinda klunky, but which
        # allows us to return all bug tasks (even private ones); this should
        # eventually be changed to a more elaborate permissions scheme,
        # pending the infrastructure to do so.
        bugtask_ids = [bugtask.id for bugtask in bugtaskset.dangerousGetAllTasks()]
        self.txn.commit()
        for bugtask_id in bugtask_ids:
            self.txn.begin()
            bugtask = bugtaskset.get(bugtask_id)
            bugtask.updateTargetNameCache()
            self.txn.commit()
        self.logger.info("Finished updating targetname cache of bugtasks.")


if __name__ == '__main__':
    script = UpdateBugTaskTargetNameCaches('launchpad-targetnamecacheupdater', 
        dbuser=config.targetnamecacheupdater.dbuser)
    script.lock_and_run(implicit_begin=False)

