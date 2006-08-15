# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Download or upload a cscvs source tree from a remote directory.

This module is the back-end for both scripts/importd-get-source.py and
scripts/importd-put-source.py.
"""

__metaclass__ = type

__all__ = ['ImportdSourceTransport']

import os
import shutil
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
        # clean up must be done before upload so failed uploads cannot
        # accumulate cruft in remote_dir
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
        tarball_file.close()

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
        self._cleanUpLocalDir()
        self._downloadTarball()
        self._extractTarball()

    def _cleanUpLocalDir(self):
        """Delete the local tarball and source tree if they exist."""
        # Deleting after testing for existence is technically racy, but it's
        # not a concern here because there should be at most one instance of a
        # job running at any time.
        local_tarball = self._localTarball()
        if os.path.exists(local_tarball):
            os.unlink(local_tarball)
        if os.path.exists(self.local_source):
            shutil.rmtree(self.local_source)

    def _downloadTarball(self):
        """Download the remote tarball into the local tarball."""
        # All remote access must be done through remote_transport.
        tarball_basename = os.path.basename(self._localTarball())
        local_file = open(self._localTarball(), 'w')
        remote_file = self.remote_transport.get(tarball_basename)
        # To keep memory usage in check, read and write in 1MB chunks.
        while True:
            data = remote_file.read(1024 * 1024)
            if not data:
                break
            local_file.write(data)
        # In principle, we should have two nested try/finally clauses, or
        # something to that effect. But if something goes wrong, we'll just let
        # the script fail, so there is no need to manually release resources.
        remote_file.close()
        local_file.close()

    def _extractTarball(self):
        """Extract contents of the local tarball into its parent directory."""
        tarball_parent, tarball_name = os.path.split(self._localTarball())
        retcode = subprocess.call(
            ['tar', 'xzf', tarball_name, '-C', tarball_parent])
        assert retcode == 0, 'tar exited with status %d' % retcode
