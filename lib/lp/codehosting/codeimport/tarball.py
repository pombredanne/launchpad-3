# Copyright 2009-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create and extract tarballs."""

__metaclass__ = type
__all__ = ['create_tarball', 'extract_tarball', 'TarError']


import os
import subprocess


class TarError(Exception):
    """Raised when the `tar` command has failed for some reason."""

    _format = 'tar exited with status %(status)d'

    def __init__(self, status):
        Exception.__init__(self, self._format % {'status': status})


class NotADirectory(Exception):

    _format = '%(path)s is not a directory.'

    def __init__(self, path):
        Exception.__init__(self, self._format % {'path': path})


def _check_tar_retcode(retcode):
    if retcode != 0:
        raise TarError(retcode)


def create_tarball(directory, tarball_name, filenames=None):
    """Create a tarball of `directory` called `tarball_name`.

    This creates a tarball of `directory` from its parent directory. This
    means that when untarred, it will create a new directory with the same
    name as `directory`. If `filenames` is not None, then the tarball will
    be limited to that list of directory entries under `directory`.

    Basically, this is the standard way of making tarballs.
    """
    if not os.path.isdir(directory):
        raise NotADirectory(directory)
    if filenames is None:
        filenames = ['.']
    retcode = subprocess.call(
        ['tar', '-C', directory, '-czf', tarball_name] + filenames)
    _check_tar_retcode(retcode)


def extract_tarball(tarball_name, directory):
    """Extract contents of a tarball.

    Changes to `directory` and extracts the tarball at `tarball_name`.
    """
    if not os.path.isdir(directory):
        raise NotADirectory(directory)
    retcode = subprocess.call(['tar', 'xzf', tarball_name, '-C', directory])
    _check_tar_retcode(retcode)
