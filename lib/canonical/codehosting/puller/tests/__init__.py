import os
import shutil
from StringIO import StringIO
import tempfile

from canonical.codehosting.puller.worker import (
    PullerWorker, PullerWorkerProtocol)


class PullerWorkerMixin:
    """Mixin for tests that want to make PullerWorker objects."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        # Change the HOME environment variable in order to ignore existing
        # user config files.
        self._home = os.environ.get('HOME', None)
        os.environ.update({'HOME': self.test_dir})

    def tearDown(self):
        if self._home is not None:
            os.environ['HOME'] = self._home
        shutil.rmtree(self.test_dir)

    def makePullerWorker(self, src_dir=None, dest_dir=None, branch_type=None,
                         protocol=None, oops_prefix=None):
        """Anonymous creation method for PullerWorker."""
        if src_dir is None:
            src_dir = os.path.join(self.test_dir, 'source_dir')
        if dest_dir is None:
            dest_dir = os.path.join(self.test_dir, 'dest_dir')
        if protocol is None:
            protocol = PullerWorkerProtocol(StringIO())
        if oops_prefix is None:
            oops_prefix = ''
        return PullerWorker(
            src_dir, dest_dir, branch_id=1, unique_name='foo/bar/baz',
            branch_type=branch_type, protocol=protocol,
            oops_prefix=oops_prefix)
