#! /usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""Perform auto-approvals and auto-blocks on translation import queue"""

import _pythonpath

from canonical.config import config
from canonical.lp import READ_COMMITTED_ISOLATION
from canonical.launchpad.scripts.po_import import AutoApproveProcess
from canonical.launchpad.scripts.base import LaunchpadCronScript


class RosettaImportApprover(LaunchpadCronScript):
    def main(self):
        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)
        process = AutoApproveProcess(self.txn, self.logger)
        self.logger.debug('Starting auto-approval of translation imports')
        process.run()
        self.logger.debug('Completed auto-approval of translation imports')


if __name__ == '__main__':
    script = RosettaImportApprover('rosetta-approve-imports',
        dbuser=config.rosetta.poimport.dbuser)
    script.lock_or_quit()
    try:
        script.run()
    finally:
        script.unlock()

