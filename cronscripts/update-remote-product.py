#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Cron job to update Product.remote_product using bug watch information.

This script sets the remote_product string value on Launchpad Products
by looking it up from one of the product's bug watches.
"""

# pylint: disable-msg=W0403
import _pythonpath

import time

from canonical.config import config
from lp.services.scripts.base import LaunchpadCronScript
from canonical.launchpad.scripts.updateremoteproduct import (
    RemoteProductUpdater)


class UpdateRemoteProduct(LaunchpadCronScript):

    def main(self):
        start_time = time.time()

        updater = RemoteProductUpdater(self.txn, self.logger)
        updater.update()

        run_time = time.time() - start_time
        self.logger.info("Time for this run: %.3f seconds." % run_time)


if __name__ == '__main__':
    script = UpdateRemoteProduct(
        "updateremoteproduct", dbuser=config.updateremoteproduct.dbuser)
    script.lock_and_run()
