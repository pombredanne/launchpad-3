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

from optparse import OptionParser

from canonical.codehosting.codeimport.worker import (
    CodeImportSourceDetails, ImportWorker, get_default_bazaar_branch_store,
    get_default_foreign_tree_store)
from canonical.launchpad import scripts



class CodeImportWorker:

    def __init__(self):
        parser = OptionParser()
        scripts.logger_options(parser)
        options, self.args = parser.parse_args()
        self.logger = scripts.logger(options, 'code-import-worker')

    def main(self):
        source_details = CodeImportSourceDetails.fromArguments(self.args)
        import_worker = ImportWorker(
            source_details, get_default_foreign_tree_store(),
            get_default_bazaar_branch_store(), self.logger)
        import_worker.run()


if __name__ == '__main__':
    script = CodeImportWorker()
    script.main()
