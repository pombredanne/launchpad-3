#!/usr/bin/python2.4

# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Expire all old, Incomplete bugs tasks that are unassigned in Malone.

Only bug task for project that use Malone may be expired. The expiration
period is configured through config.answertracker.days_before_expiration.
"""

__metaclass__ = type

import _pythonpath

from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.bugtaskexpiration import BugJanitor


class ExpireBugTasks(LaunchpadCronScript):
    """Expire all old, Incomplete bugs tasks that are unassigned in Malone.

    Only bug task for project that use Malone may be expired. The expiration
    period is configured through config.answertracker.days_before_expiration.
    """
    usage = "usage: %prog [options]"
    description =  '    %s' % self.__Doc__

    def main(self):
        """Run the BugJanitor."""
        janitor = BugJanitor(log=self.logger)
        janitor.expireBugTasks(self.txn)


if __name__ == '__main__':
    script = ExpireBugTasks(
        'expire-bugtasks', dbuser=config.answertracker.dbuser)
    script.lock_and_run()

