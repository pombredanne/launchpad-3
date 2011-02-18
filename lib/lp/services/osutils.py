# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for doing the sort of thing the os module does."""

__metaclass__ = type
__all__ = [
    'override_environ',
    'remove_tree',
    'kill_by_pidfile',
    'remove_if_exists',
    'two_stage_kill',
    'until_no_eintr',
    ]

from contextlib import contextmanager
import errno
import os.path
import shutil
import socket

from canonical.launchpad.daemons.tachandler import (
    kill_by_pidfile,
    remove_if_exists,
    two_stage_kill,
    )


def remove_tree(path):
    """Remove the tree at 'path' from disk."""
    if os.path.exists(path):
        shutil.rmtree(path)


def set_environ(new_values):
    """Set the environment variables as specified by new_values.

    :return: a dict of the old values
    """
    old_values = {}
    for name, value in new_values.iteritems():
        old_values[name] = os.environ.get(name)
        if value is None:
            if old_values[name] is not None:
                del os.environ[name]
        else:
            os.environ[name] = value
    return old_values


@contextmanager
def override_environ(**kwargs):
    """Override environment variables with the kwarg values.

    If a value is None, the environment variable is deleted.  Variables are
    restored to their previous state when exiting the context.
    """
    old_values = set_environ(kwargs)
    try:
        yield
    finally:
        set_environ(old_values)


def until_no_eintr(retries, function, *args, **kwargs):
    """Run 'function' until it doesn't raise EINTR errors.

    :param retries: The maximum number of times to try running 'function'.
    :param function: The function to run.
    :param *args: Arguments passed to the function.
    :param **kwargs: Keyword arguments passed to the function.
    :return: The return value of 'function'.
    """
    if not retries:
        return
    for i in range(retries):
        try:
            return function(*args, **kwargs)
        except (IOError, OSError), e:
            if e.errno == errno.EINTR:
                continue
            raise
        except socket.error, e:
            # In Python 2.6 we can use IOError instead.  It also has
            # reason.errno but we might be using 2.5 here so use the
            # index hack.
            if e[0] == errno.EINTR:
                continue
            raise
    else:
        raise


def ensure_directory_exists(directory, mode=0777):
    """Create 'directory' if it doesn't exist.

    :return: True if the directory had to be created, False otherwise.
    """
    try:
        os.makedirs(directory, mode=mode)
    except OSError, e:
        if e.errno == errno.EEXIST:
            return False
        raise
    return True
