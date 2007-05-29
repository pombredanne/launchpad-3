#!/usr/bin/python2.4
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

import _pythonpath

from canonical.config import config
from canonical.lp import READ_COMMITTED_ISOLATION
from canonical.launchpad.scripts.po_import import ImportProcess
from canonical.launchpad.scripts.base import LaunchpadScript


class RosettaPOImporter(LaunchpadScript):
    def main(self):
        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)
        process = ImportProcess(self.txn, self.logger)
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

