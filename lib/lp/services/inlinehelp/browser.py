# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Inline Help Support.

This package contains a base Help Folder implementation along a ZCML directive
for registering help folders.
"""

__metaclass__ = type
__all__ = [
    'HelpFolder',
    ]

from canonical.lazr.folder import ExportedFolder

class HelpFolder(ExportedFolder):
    """An exported directory containing inline help documentation."""

    export_subdirectories = True
