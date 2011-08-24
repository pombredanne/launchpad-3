#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Process a code import described by the command line arguments.

By 'processing a code import' we mean importing or updating code from a
remote, non-Bazaar, repository.

This script is usually run by the code-import-worker-monitor.py script that
communicates progress and results to the database.
"""

__metaclass__ = type


# pylint: disable-msg=W0403
import _pythonpath

from optparse import OptionParser
import sys

from bzrlib.transport import get_transport

from canonical.config import config
from lp.codehosting import load_optional_plugin
from lp.codehosting.codeimport.worker import (
    BzrSvnImportWorker, CSCVSImportWorker, CodeImportSourceDetails,
    GitImportWorker, HgImportWorker, get_default_bazaar_branch_store)
from lp.codehosting.safe_open import AcceptAnythingPolicy
from canonical.launchpad import scripts


def force_bzr_to_use_urllib():
    """Prevent bzr from using pycurl to connect to http: urls.

    We want this because pycurl rejects self signed certificates, which
    prevents a significant number of import branchs from updating.  Also see
    https://bugs.edge.launchpad.net/bzr/+bug/516222.
    """
    from bzrlib.transport import register_lazy_transport
    register_lazy_transport('http://', 'bzrlib.transport.http._urllib',
                            'HttpTransport_urllib')
    register_lazy_transport('https://', 'bzrlib.transport.http._urllib',
                            'HttpTransport_urllib')


class CodeImportWorker:

    def __init__(self):
        parser = OptionParser()
        scripts.logger_options(parser)
        options, self.args = parser.parse_args()
        self.logger = scripts.logger(options, 'code-import-worker')

    def main(self):
        force_bzr_to_use_urllib()
        source_details = CodeImportSourceDetails.fromArguments(self.args)
        if source_details.rcstype == 'git':
            load_optional_plugin('git')
            import_worker_cls = GitImportWorker
        elif source_details.rcstype == 'bzr-svn':
            load_optional_plugin('svn')
            import_worker_cls = BzrSvnImportWorker
        elif source_details.rcstype == 'hg':
            load_optional_plugin('hg')
            import_worker_cls = HgImportWorker
        elif source_details.rcstype in ['cvs', 'svn']:
            import_worker_cls = CSCVSImportWorker
        else:
            raise AssertionError(
                'unknown rcstype %r' % source_details.rcstype)
        import_worker = import_worker_cls(
            source_details,
            get_transport(config.codeimport.foreign_tree_store),
            get_default_bazaar_branch_store(), self.logger,
            AcceptAnythingPolicy())
        return import_worker.run()


if __name__ == '__main__':
    script = CodeImportWorker()
    sys.exit(script.main())
