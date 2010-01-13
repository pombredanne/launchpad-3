# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers for creating and removing a read-only.txt in the root of our tree.
"""

__metaclass__ = type
__all__ = [
    'touch_read_only_file',
    'remove_read_only_file',
    ]

import os

from canonical.launchpad.readonly import (
    read_only_file_exists, read_only_file_path)


def touch_read_only_file():
    """Create an empty file named read-only.txt under the root of the tree.

    This function must not be called if a file with that name already exists.
    """
    assert not read_only_file_exists(), (
        "This function must not be called when a read-only.txt file "
        "already exists.")
    f = open(read_only_file_path, 'w')
    f.close()


def remove_read_only_file():
    """Remove the file named read-only.txt from the root of the tree."""
    os.remove(read_only_file_path)

