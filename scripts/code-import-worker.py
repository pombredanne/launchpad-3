#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Process a code import described by the command line arguments.

By 'processing a code import' we mean importing or updating code from a
remote, non-Bazaar, repository.

This script is usually run by the code-import-worker-db.py script that
communicates progress and results to the database.
"""

__metaclass__ = type


# pylint: disable-msg=W0403
import _pythonpath

from optparse import OptionParser

from canonical.codehosting import load_optional_plugin
from canonical.codehosting.codeimport.worker import (
    CSCVSImportWorker, CodeImportSourceDetails, PullingImportWorker,
    get_default_bazaar_branch_store, get_default_foreign_tree_store)
from canonical.launchpad import scripts



class CodeImportWorker:

    def __init__(self):
        parser = OptionParser()
        scripts.logger_options(parser)
        options, self.args = parser.parse_args()
        self.logger = scripts.logger(options, 'code-import-worker')

    def main(self):
        source_details = CodeImportSourceDetails.fromArguments(self.args)
        if source_details.rcstype == 'git':
            load_optional_plugin('git')
            import_worker = PullingImportWorker(
                source_details, get_default_bazaar_branch_store(),
                self.logger)
        else:
            if source_details.rcstype not in ['cvs', 'svn']:
                raise AssertionError(
                    'unknown rcstype %r' % source_details.rcstype)
            import_worker = CSCVSImportWorker(
                source_details, get_default_foreign_tree_store(),
                get_default_bazaar_branch_store(), self.logger)
        import_worker.run()


if __name__ == '__main__':
    script = CodeImportWorker()
    script.main()
