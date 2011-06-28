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

from zope.component import getUtility

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

    def add_my_options(self):
        self.parser.add_option('-u', '--ubuntu', action='store_true',
                               dest='ubuntu', default=False,
                               help='Only expire Ubuntu bug tasks.')
        self.parser.add_option('-l', '--limit', action='store', dest='limit',
                               type='int', metavar='NUMBER', default=None,
                               help='Limit expiry to NUMBER of bug tasks.')

    def main(self):
        """Run the BugJanitor."""
        target = None
        if self.options.ubuntu:
            # Avoid circular import.
            from lp.registry.interfaces.distribution import IDistributionSet
            target = getUtility(IDistributionSet).getByName('ubuntu')
        try:
            janitor = BugJanitor(
                log=self.logger, target=target, limit=self.options.limit)
            janitor.expireBugTasks(self.txn)
        except Exception:
            # We use a catchall here because we don't know (and don't care)
            # about the particular error--we'll just log it to as an Oops.
            self.logger.error(
                'An error occured trying to expire bugtasks.', exc_info=1)
            raise


if __name__ == '__main__':
    script = ExpireBugTasks(
        'expire-bugtasks', dbuser=config.malone.expiration_dbuser)
    script.lock_and_run()
