# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Utilities for doing the sort of thing the os module does."""

__metaclass__ = type
__all__ = [
    'remove_tree',
    ]

import os
import shutil


def remove_tree(path):
    """Remove the tree at 'path' from disk."""
    if os.path.exists(path):
        shutil.rmtree(path)
