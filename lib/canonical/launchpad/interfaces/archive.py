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
    description = Text(
        title=_("Archive Contents Description"), required=False,
        description=_("A short description of contents of this Archive."))

    archive_url = Attribute("External archive URL.")

    path = TextLine(
        title=_('The on-disk location of this archive.'), required=True, 
        readonly=True
        )

    distribution = Attribute("The distribution that uses this archive.")

    purpose = Int(
        title=_("Purpose of archive."), required=True, readonly=True,
        )


    def getPubConfig(distribution):
        """Return an overridden Publisher Configuration instance.

        The original publisher configuration based on the distribution is
        modified according local context, it basically fixes the archive
        paths to cope with personal archives publication workflow.
        """


class IArchiveSet(Interface):
    """Interface for ArchiveSet"""

    title = Attribute('Title')

    def new(owner=None, purpose):
        """Create a new archive."""

    def ensure(owner=None, purpose):
        """Ensure the owner has an valid archive."""

    def get(archive_id):
        """Return the IArchive with the given archive_id."""

    def getByDistroPurpose(distribution, purpose):
        """Return the IArchive with the given distribution and purpose."""

    def getAllPPAs():
        """Return all existent personal archives."""

    def getPendingAcceptancePPAs():
        """Return only pending acceptance personal archives."""

    def getPendingPublicationPPAs():
        """Return only pending publication personal archives."""

    def __iter__():
        """Iterates over existent archives, including the main_archives."""
