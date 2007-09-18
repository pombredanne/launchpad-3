# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Archive interfaces."""

__metaclass__ = type

__all__ = [
    'IArchive',
    'IPPAActivateForm',
    'IArchiveSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Int, Text

from canonical.launchpad import _
from canonical.launchpad.interfaces import IHasOwner


class IArchive(IHasOwner):
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

    purpose = Int(
        title=_("Purpose of archive."), required=True, readonly=True,
        )

    distribution = Attribute(
        "The distribution that uses or is used by this archive.")

    archive_url = Attribute("External archive URL.")

    title = Attribute("Archive Title.")

    number_of_sources = Attribute(
        'The number of sources published in the context archive.')
    number_of_binaries = Attribute(
        'The number of binaries published in the context archive.')
    sources_size = Attribute(
        'The size of sources published in the context archive.')
    binaries_size = Attribute(
        'The size of binaries published in the context archive.')
    estimated_size = Attribute('Estimated archive size.')

    def getPubConfig():
        """Return an overridden Publisher Configuration instance.

        The original publisher configuration based on the distribution is
        modified according local context, it basically fixes the archive
        paths to cope with non-primary and PPA archives publication workflow.
        """

    def getPublishedSources():
        """All `ISourcePackagePublishingHistory` target to this archive.

        :return: SelectResults containing `ISourcePackagePublishingHistory`.
        """

    def getPublishedBinaries():
        """All `IBinaryPackagePublishingHistory` target to this archive.

        :return: SelectResults containing `IBinaryPackagePublishingHistory`.
        """

    def allowUpdatesToReleasePocket():
        """Return whether the archive allows publishing to the release pocket.

        If a distroseries is stable, normally release pocket publishings are
        not allowed.  However some archive types allow this.

        :return: True or False
        """

class IPPAActivateForm(Interface):
    """Schema used to activate PPAs."""

    description = Text(
        title=_("PPA contents description"), required=False,
        description=_(
        "A short description of contents and goals of this PPA. This text "
        "will be presented in the PPA page and will also allow other users "
        "to find your PPA in their searches. URLs are allowed and will "
        "be rendered as links."))

    accepted = Bool(
        title=_("I accept the PPA Terms of Service."),
        required=True, default=False)


class IArchiveSet(Interface):
    """Interface for ArchiveSet"""

    title = Attribute('Title')

    def new(distribution=None, purpose=None, owner=None, description=None):
        """Create a new archive.

        If purpose is ArchivePurpose.PPA, owner must be set.
        """

    def ensure(owner, distribution, purpose, description):
        """Ensure the owner has a valid archive."""

    def get(archive_id):
        """Return the IArchive with the given archive_id."""

    def getByDistroPurpose(distribution, purpose):
        """Return the IArchive with the given distribution and purpose."""

    def __iter__():
        """Iterates over existent archives, including the main_archives."""
