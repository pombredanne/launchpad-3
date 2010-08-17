# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for doing the sort of thing the os module does."""

__metaclass__ = type
__all__ = [
    'override_environ',
    'remove_tree',
    'kill_by_pidfile',
    'remove_if_exists',
    'two_stage_kill',
    ]

from contextlib import contextmanager
import os.path
import shutil


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
