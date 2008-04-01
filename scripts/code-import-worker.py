#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""When passed a CodeImportJob id on the command line, process that job.

By 'processing a job' we mean importing or updating a code import from
a remote, non-Bazaar, repository.

This script is usually run by the code-import-dispatcher cronscript.
"""

__metaclass__ = type


# pylint: disable-msg=W0403
import _pythonpath

from canonical.codehosting.codeimport.worker import (
    ImportWorker, get_default_bazaar_branch_store,
    get_default_foreign_tree_store)
from canonical.launchpad.scripts.base import LaunchpadScript


class CodeImportWorker(LaunchpadScript):
    def main(self):
        [job_id] = self.args
        job_id = int(job_id)
        import_worker = ImportWorker(
            job_id, get_default_foreign_tree_store(),
            get_default_bazaar_branch_store(), self.logger)
        import_worker.run()


if __name__ == '__main__':
    script = CodeImportWorker(
        'code-import-worker', dbuser='importd')
    script.lock_and_run()
