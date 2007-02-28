# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Archive interfaces."""

__metaclass__ = type

__all__ = [
    'IArchive',
    'IArchiveSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Text

from canonical.launchpad import _


class IArchive(Interface):
    """An Archive interface"""

    id = Attribute("The archive ID.")

    owner = Attribute("The owner of the archive, or None for the main "
                      "archive of a distribution")

    def getPubConfig(distribution):
        """Return an overridden Publisher Configuration instance.

        The original publisher configuration based on the distribution is
        modified according local context, it basically fixes the archive
        paths to cope with personal archives publication workflow.
        """


class IArchiveSet(Interface):
    """Interface for ArchiveSet"""

    title = Attribute('Title')

    def new(owner=None):
        """Create a new archive."""

    def get(archive_id):
        """Return the IArchive with the given archive_id."""

    def getAllPPAs():
        """Return all existent personal archives."""

    def __iter__():
        """Iterates over existent archives, including the main_archives."""
