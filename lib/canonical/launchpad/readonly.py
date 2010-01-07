# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for running Launchpad in read-only mode.

To switch an app server to read-only mode, all you need to do is create a file
named read-only.txt under the root of the Launchpad tree.
"""

import os


root = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
file_path = os.path.join(root, 'read-only.txt')


def is_read_only():
    """Are we in read-only mode?

    Use with caution as this function will hit the filesystem to check for the
    presence of a file.
    """
    return os.path.isfile(file_path)


def touch_read_only_file():
    """Create an empty file named read-only.txt under the root of the tree.

    This function must not be called if a file with that name already exists.
    """
    assert not is_read_only(), (
        "This function must not be called when a read-only.txt file "
        "already exists.")
    f = open(file_path, 'w')
    f.close()


def remove_read_only_file():
    """Remove the file named read-only.txt from the root of the tree."""
    os.remove(file_path)
