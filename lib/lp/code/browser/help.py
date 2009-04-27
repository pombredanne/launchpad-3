# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Help folder view."""

__metaclass__ = type
__all__ = []

import os.path

from canonical.lazr.folder import ExportedFolder


class CodeHelpFolder(ExportedFolder):
    """Export the Code help folder."""

    folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../help/')

