# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Archive interfaces."""

__metaclass__ = type

__all__ = [
    'IArchive',
    'IArchiveSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Text, Choice, Int, Bool

from canonical.launchpad import _
from canonical.launchpad.interfaces import IHasOwner


class IArchive(Interface, IHasOwner):
    """An Archive interface"""

    id = Attribute("The archive ID.")

    owner = Choice(
        title=_('Owner'), required=True, vocabulary='ValidOwner',
        description=_("""The PPA owner."""))

    description = Text(
        title=_("PPA contents description"), required=False,
        description=_("A short description of contents of this PPA."))

    enabled = Bool(
        title=_("Enabled"), required=False,
        description=_("Whether the PPA is enabled or not."))

    authorized_size = Int(
        title=_("Authorized PPA size "), required=False,
        description=_("Maximum size, in bytes, allowed for this PPA."))

    whiteboard = Text(
        title=_("Whiteboard"), required=False,
        description=_("Administrator comments."))


    archive_url = Attribute("External archive URL.")
    title = Attribute("Archive Title.")
    distribution = Attribute('Distribution related to this Archive.')

    def getPubConfig(distribution):
        """Return an overridden Publisher Configuration instance.

        The original publisher configuration based on the distribution is
        modified according local context, it basically fixes the archive
        paths to cope with personal archives publication workflow.
        """

    def getPublishedSources():
        """Return all ISourcePackagePublishingHistory target to this archive."""


class IArchiveSet(Interface):
    """Interface for ArchiveSet"""

    title = Attribute('Title')

    def new(owner=None, description=None):
        """Create a new archive."""

    def ensure(owner=None):
        """Ensure the owner has an valid archive."""

    def get(archive_id):
        """Return the IArchive with the given archive_id."""

    def getAllPPAs():
        """Return all existent personal archives."""

    def searchPPAs(text=None):
        """Return all existent personal archives matching the given text."""

    def getPendingAcceptancePPAs():
        """Return only pending acceptance personal archives."""

    def getPendingPublicationPPAs():
        """Return only pending publication personal archives."""

    def __iter__():
        """Iterates over existent archives, including the main_archives."""
