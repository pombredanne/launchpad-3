# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for doing the sort of thing the os module does."""

__metaclass__ = type
__all__ = [
    'remove_tree',
    'kill_by_pidfile',
    'remove_if_exists',
    'two_stage_kill',
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


def two_stage_kill(pid, poll_interval=0.1, num_polls=50):
    """Kill process 'pid' with SIGTERM. If it doesn't die, SIGKILL it.

    :param pid: The pid of the process to kill.
    :param poll_interval: The polling interval used to check if the
        process is still around.
    :param num_polls: The number of polls to do before doing a SIGKILL.
    """
    # Kill the process.
    try:
        os.kill(pid, SIGTERM)
    except OSError, e:
        if e.errno in (errno.ESRCH, errno.ECHILD):
            # Process has already been killed.
            return

    # Poll until the process has ended.
    for i in range(num_polls):
        try:
            # Reap the child process. Without this, os.kill will think that
            # the child process is still running.
            os.waitpid(pid, os.WNOHANG)
            # Don't send a signal, but raise an error if the process doesn't
            # exist. That is, if the process has been terminated.
            os.kill(pid, 0)
            time.sleep(poll_interval)
        except OSError, e:
            break
    else:
        # The process is still around, so terminate it violently.
        try:
            os.kill(pid, SIGKILL)
        except OSError:
            # Already terminated
            pass


def kill_by_pidfile(pidfile_path):
    """Kill a process identified by the pid stored in a file.

    The pid file is removed from disk.
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

        two_stage_kill(pid)
    finally:
        remove_if_exists(pidfile_path)


def remove_if_exists(path):
    """Remove the given file if it exists."""
    try:
        os.remove(path)
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise
