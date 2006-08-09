# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Download or upload a cscvs source tree from a remote directory.

This module is the back-end for both scripts/importd-get-source.py and
scripts/importd-put-source.py.
"""

__metaclass__ = type

__all__ = ['ImportdSourceTransport']

import os
import subprocess

from bzrlib.errors import NoSuchFile
from bzrlib.transport import get_transport

class ImportdSourceTransport:
    """Download or upload a cscvs source tree from a remote directory."""

    # File transfers are done using the bzrlib transport system. That provides
    # an easy API to Paramiko and protocol transparency so tests do not require
    # a SFTP server.

    def __init__(self, log, local_source, remote_dir):
        self.logger = log
        self.local_source = local_source
        self.remote_dir = remote_dir
        self.remote_transport = get_transport(remote_dir)

    def putImportdSource(self):
        """Upload a cscvs source tree."""
        self._createTarball()
        self._cleanUpRemoteDir()
        self._uploadTarball()
        self._finalizeUpload()

    def _createTarball(self):
        """Create a tarball of the source tree."""
        source_parent, source_name = os.path.split(self.local_source)
        local_tarball = self._localTarball()
        retcode = subprocess.call(
            ['tar', 'czf', local_tarball, source_name, '-C', source_parent])
        assert retcode == 0, 'tar exited with status %d' % retcode

    def _localTarball(self):
        """Name of the local tarball file."""
        local_tarball = self.local_source + '.tgz'
        # Assert that we generate the filename that we want.
        # That can fail e.g. if local_source ends with a path delimiter.
        assert (os.path.basename(local_tarball)
                == os.path.basename(self.local_source) + '.tgz')
        assert (os.path.dirname(local_tarball)
                == os.path.dirname(self.local_source))
        return local_tarball

    def _uploadTarball(self):
        """Upload the local tarball to a swap file in the remote dir."""
        # All remote access must be done through remote_transport.
        swap_basename = os.path.basename(self._localTarball() + '.swp')
        tarball_file = open(self._localTarball())
        try:
            self.remote_transport.put(swap_basename, tarball_file)
        except NoSuchFile:
            # remote_dir does not exist, create it. We do try not create any
            # parent of remote_dir, because the expected usage is to have the
            # remote_dirs for all imports stored flat in a common base
            # directory. If the base directory is incorrect, we want to fail.
            parent_transport = self.remote_transport.clone('..')
            needed = parent_transport.relpath(self.remote_dir)
            parent_transport.mkdir(needed)
            self.remote_transport.put(swap_basename, tarball_file)

    def _finalizeUpload(self):
        """Move the remote swap file over to the remote tarball name."""
        # All remote access must be done through remote_transport.
        tarball_basename = os.path.basename(self._localTarball())
        swap_basename = tarball_basename + '.swp'
        self.remote_transport.move(swap_basename, tarball_basename)

    def _cleanUpRemoteDir(self):
        """Remove any file present in remote_dir except the source tarball."""
        # All remote access must be done through remote_transport.
        tarball_basename = os.path.basename(self._localTarball())
        try:
            entries = self.remote_transport.list_dir('.')
        except NoSuchFile:
            # remote_dir does not exist, nothing to clean up!
            return
        to_delete = [entry for entry in entries if entry != tarball_basename]
        self.remote_transport.delete_multi(to_delete)

    def getImportdSource(self):
        """Download a cscvs source tree."""
        # XXX: stub for testing
        os.mkdir(self.local_source)

    def _remoteTarball(self):
        # XXX: use url arithmetic!
        return os.path.join(self.remote_dir,
                            os.path.basename(self.local_source)) + '.tgz'
