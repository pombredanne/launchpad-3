# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Archive interfaces."""

__metaclass__ = type

__all__ = [
    'IArchive',
    'IArchiveSet',
    ]

from zope.interface import Interface, Attribute

from canonical.launchpad import _


class IArchive(Interface):
    """An Archive interface"""
    id = Attribute("The archive ID.")

class IArchiveSet(Interface):
    """Interface for ArchiveSet"""

    title = Attribute('Title')

    def new():
        """Create a new archive."""

    def get(archiveid):
        """Return the IArchive with the given archiveid."""

