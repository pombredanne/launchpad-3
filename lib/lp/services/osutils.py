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
