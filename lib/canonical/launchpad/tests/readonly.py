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
    is_read_only, read_only_file_exists, read_only_file_path)


def touch_read_only_file():
    """Create an empty file named read-only.txt under the root of the tree.

    This function must not be called if a file with that name already exists.
    """
    assert not read_only_file_exists(), (
        "This function must not be called when a read-only.txt file "
        "already exists.")
    f = open(read_only_file_path, 'w')
    f.close()
    # Assert that the switch succeeded and make sure the mode change is
    # logged.
    assert is_read_only(), "Switching to read-only failed."


def remove_read_only_file(assert_mode_switch=True):
    """Remove the file named read-only.txt from the root of the tree.

    May also assert that the mode switch actually happened (i.e. not 
    is_read_only()). This assertion has to be conditional because some tests
    will use this during the processing of a request, when a mode change can't
    happen (i.e. is_read_only() will still return True during that request's
    processing, even though the read-only.txt file has been removed).
    """
    os.remove(read_only_file_path)
    if assert_mode_switch:
        # Assert that the switch succeeded and make sure the mode change is
        # logged.
        assert not is_read_only(), "Switching to read-write failed."
