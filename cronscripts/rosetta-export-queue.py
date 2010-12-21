#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

import _pythonpath

from canonical.database.sqlbase import ISOLATION_LEVEL_READ_COMMITTED
from lp.translations.scripts.po_export_queue import process_queue
from lp.services.scripts.base import LaunchpadCronScript


class RosettaExportQueue(LaunchpadCronScript):
    def main(self):
        self.txn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        process_queue(self.txn, self.logger)


if __name__ == '__main__':
    script = RosettaExportQueue('rosetta-export-queue', dbuser='poexport')
    script.lock_and_run()

