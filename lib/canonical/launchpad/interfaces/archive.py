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

    owner = Attribute("The owner of the archive, or None for the main "
                      "archive of a distribution")

class IArchiveSet(Interface):
    """Interface for ArchiveSet"""

    title = Attribute('Title')

    def new(tag, owner=None):
        """Create a new archive."""

    def get(archiveid):
        """Return the IArchive with the given archiveid."""

