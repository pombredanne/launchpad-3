# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for doing the sort of thing the os module does."""

__metaclass__ = type
__all__ = [
    'remove_tree',
    'kill_by_pidfile',
    'remove_if_exists',
    ]

import errno
import os.path
from signal import SIGTERM, SIGKILL
import shutil
import time


def remove_tree(path):
    """Remove the tree at 'path' from disk."""
    if os.path.exists(path):
        shutil.rmtree(path)


def kill_by_pidfile(pidfile_path, remove=True):
    """Kill a process identified by the pid stored in a file.

    :param remove: If True, the pidfile_path is removed on success.
    """
    if not os.path.exists(pidfile_path):
        return
    try:
        # Get the pid.
        pid = open(pidfile_path, 'r').read().split()[0]
        try:
            pid = int(pid)
        except ValueError:
            # pidfile contains rubbish
            return

        # Kill the process.
        try:
            os.kill(pid, SIGTERM)
        except OSError, e:
            if e.errno in (errno.ESRCH, errno.ECHILD):
                # Process has already been killed.
                return

        # Poll until the process has ended.
        for i in range(50):
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except OSError, e:
                break
        else:
            # The process is still around, so terminate it violently.
            try:
                os.kill(pid, SIGKILL)
            except OSError:
                # Already terminated
                pass
    finally:
        if remove:
            remove_if_exists(pidfile_path)


def remove_if_exists(path):
    """Remove the given file if it exists."""
    try:
        os.remove(path)
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise
