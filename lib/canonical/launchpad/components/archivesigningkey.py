# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ArchiveSigningKey implementation."""

__metaclass__ = type

__all__ = [
    'ArchiveSigningKey',
    ]


from zope.interface import implements

from canonical.launchpad.interfaces.archivesigningkey import (
    IArchiveSigningKey)


class ArchiveSigningKey:
    """`IArchive` adapter for manipulating its GPG key."""

    implements(IArchiveSigningKey)

    def __init__(self, archive):
        self.archive = archive

    def generateSigningKey(self):
        """See `IArchiveSigningKey`."""
        pass

    def signRepository(self):
        """See `IArchiveSigningKey`."""
        pass

