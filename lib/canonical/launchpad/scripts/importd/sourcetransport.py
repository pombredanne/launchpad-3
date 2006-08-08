# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Download or upload a cscvs source tree from a remote directory.

This module is the back-end for both scripts/importd-get-source.py and
scripts/importd-put-source.py.
"""

__metaclass__ = type

__all__ = ['ImportdSourceTransport']

import os


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

    def getImportdSource(self):
        """Download a cscvs source tree."""
        os.mkdir(self.local_source)

    def _remoteTarball(self):
        # XXX: use url arithmetic!
        return os.path.join(self.remote_dir,
                            os.path.basename(self.local_source)) + '.tgz'

    def putImportdSource(self):
        """Upload a cscvs source tree."""
        open(self._remoteTarball(), 'w').close()
