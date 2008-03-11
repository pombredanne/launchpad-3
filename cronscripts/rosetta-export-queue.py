#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd. All rights reserved.
# pylint: disable-msg=C0103,W0403

import _pythonpath

from canonical.database.sqlbase import ISOLATION_LEVEL_READ_COMMITTED
from canonical.launchpad.scripts.po_export_queue import process_queue
from canonical.launchpad.scripts.base import LaunchpadCronScript


class RosettaExportQueue(LaunchpadCronScript):
    def main(self):
        self.txn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        process_queue(self.txn, self.logger)


if __name__ == '__main__':
    script = RosettaExportQueue('rosetta-export-queue', dbuser='poexport')
    script.lock_and_run()

