#!/usr/bin/python2.4
# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

import _pythonpath

from canonical.config import config
from canonical.lp import READ_COMMITTED_ISOLATION
from canonical.launchpad.scripts.po_import import ImportProcess
from canonical.launchpad.scripts.base import LaunchpadCronScript

# Time goal for this run.  It is not exact.  The script will run for longer
# than this time, but will know to stop taking on new batches of imports.
# Since script is run every 9 or 10 minutes, we set the "alarm" at 8 minutes.
# That leaves a bit of time to complete the last ongoing batch of imports.
SECONDS_TO_RUN = 8 * 60

class RosettaPOImporter(LaunchpadCronScript):
    def main(self):
        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)
        process = ImportProcess(self.txn, self.logger, SECONDS_TO_RUN)
        self.logger.debug('Starting the import process')
        process.run()
        self.logger.debug('Finished the import process')


if __name__ == '__main__':
    script = RosettaPOImporter('rosetta-poimport',
        dbuser=config.rosetta.poimport.dbuser)
    script.lock_or_quit()
    try:
        script.run()
    finally:
        script.unlock()

