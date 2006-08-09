# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Download or upload a cscvs source tree from a remote directory.

This module is the back-end for both scripts/importd-get-source.py and
scripts/importd-put-source.py.
"""

__metaclass__ = type

__all__ = ['ImportdSourceTransport']

import os
import subprocess


class ImportdSourceTransport:
    """Download or upload a cscvs source tree from a remote directory.

    File transfers are done using the bzrlib transport system. That provides an
    easy API to Paramiko and protocol transparency so tests do not require a
    SFTP server.
    """

    def __init__(self, log, local_source, remote_dir):
        self.logger = log
        self.local_source = local_source
        self.remote_dir = remote_dir

    def putImportdSource(self):
        """Upload a cscvs source tree."""
        self._createTarball()
        # XXX: stub for testing
        os.rename(self.local_source + '.tgz', self._remoteTarball())

    def _createTarball(self):
        """Create a tarball of the source tree."""
        source_parent, source_name = os.path.split(self.local_source)
        retcode = subprocess.call(
            ['tar', 'czf', self.local_source + '.tgz',
             source_name, '-C', source_parent])
        assert retcode == 0, 'tar exited with status %d' % retcode

    def getImportdSource(self):
        """Download a cscvs source tree."""
        # XXX: stub for testing
        os.mkdir(self.local_source)

    def _remoteTarball(self):
        # XXX: use url arithmetic!
        return os.path.join(self.remote_dir,
                            os.path.basename(self.local_source)) + '.tgz'

