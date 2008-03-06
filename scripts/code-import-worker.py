# Copyright 2008 Canonical Ltd.  All rights reserved.

"""When passed a CodeImportJob id on the command line, process that job."""

__metaclass__ = type


import _pythonpath

from bzrlib.transport import get_transport

from canonical.codehosting.codeimport.worker import (
    ImportWorker, BazaarBranchStore, ForeignTreeStore)
from canonical.config import config
from canonical.launchpad.scripts.base import LaunchpadScript

class CodeImportWorker(LaunchpadScript):
    def main(self):
        [job_id] = self.args
        job_id = int(job_id)
        bazaar_branch_store = BazaarBranchStore(
            get_transport(config.something))
        foreign_tree_store = ForeignTreeStore(
            get_transport(config.something_else))
        import_worker = ImportWorker(
            job_id, foreign_tree_store, bazaar_branch_store, self.logger)
        import_worker.run()

if __name__ == '__main__':
    script = CodeImportWorker(
        'code-import-worker', dbuser='importd')
    script.lock_and_run()
