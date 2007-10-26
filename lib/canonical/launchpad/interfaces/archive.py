# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Archive interfaces."""

__metaclass__ = type

__all__ = [
    'ArchivePurpose',
    'IArchive',
    'IPPAActivateForm',
    'IArchiveSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice, Int, Text

from canonical.launchpad import _
from canonical.launchpad.interfaces import IHasOwner
from canonical.lazr import DBEnumeratedType, DBItem


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

    series_with_sources = Attribute(
        "DistroSeries to which this archive has published sources")
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

    def getPublishedSources(name=None, version=None, status=None,
                            distroseries=None, exact_match=False):
        """All `ISourcePackagePublishingHistory` target to this archive.

        :param: name: source name filter (exact match or SQL LIKE controlled
                      by 'exact_match' argument).
        :param: version: source version filter (always exact match).
        :param: status: `PackagePublishingStatus` filter, can be a list.
        :param: distroseries: `IDistroSeries` filter.
        :param: exact_match: either or not filter source names by exact
                             matching.

        :return: SelectResults containing `ISourcePackagePublishingHistory`.
        """

    def getPublishedOnDiskBinaries(name=None, version=None, status=None,
                                   distroarchseries=None, exact_match=False):
        """Unique `IBinaryPackagePublishingHistory` target to this archive.

        In spite of getAllPublishedBinaries method, this method only returns
        distinct binary publications inside this Archive, i.e, it excludes
        architecture-independent publication for other architetures than the
        nominatedarchindep. In few words it represents the binary files
        published in the archive disk pool.

        :param: name: binary name filter (exact match or SQL LIKE controlled
                      by 'exact_match' argument).
        :param: version: binary version filter (always exact match).
        :param: status: `PackagePublishingStatus` filter, can be a list.
        :param: distroarchseries: `IDistroArchSeries` filter, can be a list.
        :param: exact_match: either or not filter source names by exact
                             matching.

        :return: SelectResults containing `IBinaryPackagePublishingHistory`.
        """

    def getAllPublishedBinaries(name=None, version=None, status=None,
                                distroarchseries=None, exact_match=False):
        """All `IBinaryPackagePublishingHistory` target to this archive.

        See getUniquePublishedBinaries for further information.

        :param: name: binary name filter (exact match or SQL LIKE controlled
                      by 'exact_match' argument).
        :param: version: binary version filter (always exact match).
        :param: status: `PackagePublishingStatus` filter, can be a list.
        :param: distroarchseries: `IDistroArchSeries` filter, can be a list.
        :param: exact_match: either or not filter source names by exact
                             matching.

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
        "A short description of this PPA. This text URLs are allowed and will "
        "be rendered as links."))

    accepted = Bool(
        title=_("I have read and accepted the PPA Terms of Service."),
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

    def getPPAByDistributionAndOwnerName(distribution, name):
        """Return a single PPA the given (distribution, name) pair."""

    def getByDistroPurpose(distribution, purpose):
        """Return the IArchive with the given distribution and purpose."""

    def __iter__():
        """Iterates over existent archives, including the main_archives."""

class ArchivePurpose(DBEnumeratedType):
    """The purpose, or type, of an archive.

    A distribution can be associated with different archives and this
    schema item enumerates the different archive types and their purpose.
    For example, old distro releases may need to be obsoleted so their
    archive would be OBSOLETE_ARCHIVE.
    """

    PRIMARY = DBItem(1, """
        Primary Archive

        This is the primary Ubuntu archive.
        """)

    PPA = DBItem(2, """
        PPA Archive

        This is a Personal Package Archive.
        """)

    EMBARGOED = DBItem(3, """
        Embargoed Archive

        This is the archive for embargoed packages.
        """)

    PARTNER = DBItem(4, """
        Partner Archive

        This is the archive for partner packages.
        """)

    OBSOLETE = DBItem(5, """
        Obsolete Archive

        This is the archive for obsolete packages.
        """)

