#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

"""Expire all old, Incomplete bugs tasks that are unassigned in Malone.

Only bug task for project that use Malone may be expired. The expiration
period is configured through config.malone.days_before_expiration.
"""

__metaclass__ = type

import _pythonpath

from canonical.config import config
from lp.services.scripts.base import LaunchpadCronScript
from lp.bugs.scripts.bugexpire import BugJanitor


class ExpireBugTasks(LaunchpadCronScript):
    """Expire all old, Incomplete bugs tasks that are unassigned in Malone.

    Only bug task for project that use Malone may be automatically set to
    the status of Invalid (expired). The expiration period is configured
    through config.malone.days_before_expiration.
    """
    usage = "usage: %prog [options]"
    description =  '    %s' % __doc__

    def main(self):
        """Run the BugJanitor."""
        janitor = BugJanitor(log=self.logger)
        janitor.expireBugTasks(self.txn)


if __name__ == '__main__':
    script = ExpireBugTasks(
        'expire-bugtasks', dbuser=config.malone.expiration_dbuser)
    script.lock_and_run()

