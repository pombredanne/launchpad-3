# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Publishing interfaces."""

__metaclass__ = type

__all__ = [
    'ISourcePackageFilePublishing',
    'IBinaryPackageFilePublishing',
    'ISecureSourcePackagePublishingHistory',
    'ISecureBinaryPackagePublishingHistory',
    'ISourcePackagePublishingHistory',
    'IBinaryPackagePublishingHistory',
    'ICanPublishPackages',
    'IFilePublishing',
    'IArchiveSafePublisher',
    'NotInPool',
    'PackagePublishingPocket',
    'PackagePublishingPriority',
    'PackagePublishingStatus',
    'PoolFileOverwriteError',
    'pocketsuffix'
    ]

from zope.schema import Bool, Datetime, Int, TextLine, Text
from zope.interface import Interface, Attribute

from canonical.launchpad import _

from canonical.lazr import DBEnumeratedType, DBItem

#
# Exceptions
#


class NotInPool(Exception):
    """Raised when an attempt is made to remove a non-existent file."""


class PoolFileOverwriteError(Exception):
    """Raised when an attempt is made to overwrite a file in the pool.

    The proposed file has different content as the one in pool.
    This exception is unexpected and when it happens we keep the original
    file in pool and print a warning in the publisher log. It probably
    requires manual intervention in the archive.
    """


#
# Base Interfaces
#

class ICanPublishPackages(Interface):
    """Denotes the ability to publish associated publishing records."""

    def getPendingPublications(archive, pocket, is_careful):
        """Return the specific group of records to be published.

        IDistroSeries -> ISourcePackagePublishing
        IDistroArchSeries -> IBinaryPackagePublishing

        'pocket' & 'archive' are mandatory arguments, they  restrict the
        results to the given value.

        If the distroseries is already released, it automatically refuses
        to publish records to RELEASE pocket.
        """

    def publish(diskpool, log, archive, pocket, careful=False):
        """Publish associated publishing records targeted for a given pocket.

        Require an initialised diskpool instance and a logger instance.
        Require an 'archive' which will restrict the publications.
        'careful' argument would cause the 'republication' of all published
        records if True (system will DTRT checking hash of all
        published files.)

        Consider records returned by the local implementation of
        getPendingPublications.
        """


class IArchiveSafePublisher(Interface):
    """Safe Publication methods"""

    def setPublished():
        """Set a publishing record to published.

        Basically set records to PUBLISHED status only when they
        are PENDING and do not update datepublished value of already
        published field when they were checked via 'careful'
        publishing.
        """


class IPublishing(Interface):
    """Base interface for all *Publishing classes"""

    files = Attribute("Files included in this publication.")
    secure_record = Attribute("Correspondent secure package history record.")
    displayname = Attribute("Text representation of the current record.")
    age = Attribute("Age of the publishing record.")

    def publish(diskpool, log):
        """Publish or ensure contents of this publish record

        Skip records which attempt to overwrite the archive (same file paths
        with different content) and do not update the database.

        If all the files get published correctly update its status properly.
        """

    def getIndexStanza():
        """Return archive index stanza contents

        It's based on the locally provided buildIndexStanzaTemplate method,
        which differs for binary and source instances.
        """

    def buildIndexStanzaFields():
        """Build a map of fields and values to be in the Index file.

        The fields and values ae mapped into a dictionary, where the key is
        the field name and value is the value string.
        """

    def supersede():
        """Supersede this publication.

        :return: The superseded publishing records, either a
            `ISourcePackagePublishingHistory` or
            `IBinaryPackagePublishingHistory`.
        """

    def requestDeletion(removed_by, removal_comment=None):
        """Delete this publication.

        :param removed_by: `IPerson` responsible for the removal.
        :param removal_comment: optional text describing the removal reason.

        :return: The deleted publishing record, either:
            `ISourcePackagePublishingHistory` or
            `IBinaryPackagePublishingHistory`.
        """

    def requestObsolescence():
        """Make this publication obsolete.

        :return: The obsoleted publishing record, either:
            `ISourcePackagePublishingHistory` or
            `IBinaryPackagePublishingHistory`.
        """

    def copyTo(distroseries, pocket, archive):
        """Copy this publication to another location.

        :return: The publishing in the targeted location, either:
            `ISourcePackagePublishingHistory` or
            `IBinaryPackagePublishingHistory`.
        """


class IFilePublishing(Interface):
    """Base interface for *FilePublishing classes"""

    distribution = Int(
            title=_('Distribution ID'), required=True, readonly=True,
            )
    distroseriesname = TextLine(
            title=_('Series name'), required=True, readonly=True,
            )
    componentname = TextLine(
            title=_('Component name'), required=True, readonly=True,
            )
    publishingstatus = Int(
            title=_('Package publishing status'), required=True,
            readonly=True,
            )
    pocket = Int(
            title=_('Package publishing pocket'), required=True,
            readonly=True,
            )
    archive = Int(
            title=_('Archive ID'), required=True, readonly=True,
            )
    libraryfilealias = Int(
            title=_('Binarypackage file alias'), required=True,
            readonly=True,
            )
    libraryfilealiasfilename = TextLine(
            title=_('File name'), required=True, readonly=True,
            )
    archive_url = Attribute('The on-archive URL for the published file.')

    publishing_record = Attribute(
        "Return the Source or Binary publishing record "
        "(in the form of I{Source,Binary}PackagePublishingHistory).")

    def publish(diskpool, log):
        """Publish or ensure contents of this file in the archive.

        Create symbolic link to files already present in different component
        or add file from librarian if it's not present. Update the database
        to represent the current archive state.
        """

#
# Source package publishing
#

class ISourcePackageFilePublishing(IFilePublishing):
    """Source package release files and their publishing status"""
    file_type_name = Attribute(
        "The uploaded file's type; one of 'orig', 'dsc', 'diff' or 'other'")
    sourcepackagename = TextLine(
            title=_('Binary package name'), required=True, readonly=True,
            )
    sourcepackagepublishing = Int(
            title=_('Sourcepackage publishing record id'), required=True,
            readonly=True,
            )


class ISecureSourcePackagePublishingHistory(IPublishing):
    """A source package publishing history record."""
    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    sourcepackagerelease = Int(
            title=_('The source package release being published'),
            required=False, readonly=False,
            )
    status = Int(
            title=_('The status of this publishing record'),
            required=False, readonly=False,
            )
    distroseries = Int(
            title=_('The distroseries being published into'),
            required=False, readonly=False,
            )
    component = Int(
            title=_('The component being published into'),
            required=False, readonly=False,
            )
    section = Int(
            title=_('The section being published into'),
            required=False, readonly=False,
            )
    datepublished = Datetime(
            title=_('The date on which this record was published'),
            required=False, readonly=False,
            )
    scheduleddeletiondate = Datetime(
            title=_('The date on which this record is scheduled for '
                    'deletion'),
            required=False, readonly=False,
            )
    pocket = Int(
            title=_('The pocket into which this entry is published'),
            required=True, readonly=True,
            )
    archive = Int(
            title=_('Archive ID'), required=True, readonly=True,
            )
    supersededby = Int(
            title=_('The sourcepackagerelease which superseded this one'),
            required=False, readonly=False,
            )
    datesuperseded = Datetime(
            title=_('The date on which this record was marked superseded'),
            required=False, readonly=False,
            )
    datecreated = Datetime(
            title=_('The date on which this record was created'),
            required=True, readonly=False,
            )
    datemadepending = Datetime(
            title=_('The date on which this record was set as pending '
                    'removal'),
            required=False, readonly=False,
            )
    dateremoved = Datetime(
            title=_('The date on which this record was removed from the '
                    'published set'),
            required=False, readonly=False,
            )
    embargo = Bool(
            title=_('Whether or not this record is under embargo'),
            required=True, readonly=False,
            )
    embargolifted = Datetime(
            title=_('The date on which this record had its embargo lifted'),
            required=False, readonly=False,
            )
    removed_by = Int(
        title=_('The IPerson responsible for the removal'),
        required=False, readonly=False,
        )
    removal_comment = Text(
        title=_('Reason why this publication is going to be removed.'),
        required=False, readonly=False,
        )


class ISourcePackagePublishingHistory(ISecureSourcePackagePublishingHistory):
    """A source package publishing history record."""
    meta_sourcepackage = Attribute(
        "Return an ISourcePackage meta object correspondent to the "
        "sourcepackagerelease attribute inside a specific distroseries")
    meta_sourcepackagerelease = Attribute(
        "Return an IDistribuitionSourcePackageRelease meta object "
        "correspondent to the sourcepackagerelease attribute")
    meta_supersededby = Attribute(
        "Return an IDistribuitionSourcePackageRelease meta object "
        "correspondent to the supersededby attribute. if supersededby "
        "is None return None.")
    meta_distroseriessourcepackagerelease = Attribute(
        "Return an IDistroSeriesSourcePackageRelease meta object "
        "correspondent to the sourcepackagerelease attribute inside "
        "a specific distroseries")

    def getPublishedBinaries():
        """Return all resulted IBinaryPackagePublishingHistory.

        Follow the build record and return every PUBLISHED binary publishing
        record for DistroArchSeries in this DistroSeries and in the same
        Pocket, ordered by architecturetag.
        """

    def getBuilds():
        """Return `IBuild` objects in this SourcePackageRelease` context.

        The builds are ordered by `DistroArchSeries.architecturetag`.
        """

    def createMissingBuilds(ignore_pas=False, logger=None):
        """Create missing Build records for a published source.

        P-a-s should be only initialised and considered when accepting
        sources to the PRIMARY archive (in drescher). It explicitly ignores
        P-a-s for sources targeted to PPAs.

        :param ignore_pas: whether or not to initialise and respect
             Package-architecture-specific (P-a-s) for creating builds;
        :param logger: optional context Logger object (used on DEBUG level).

        :return: a list of `Builds` created for this source publication.
        """

    def getSourceAndBinaryLibraryFiles():
        """Return LibraryFileAlias records for all source and binaries.

        All the published source and binary files associated with this
        source publishing are returned as LibraryFileAlias records.
        """

    def changeOverride(new_component=None, new_section=None):
        """Change the component and/or section of this publication

        It is changed only if the argument is not None.

        Return the overridden publishing record, either a
        `ISourcePackagePublishingHistory` or `IBinaryPackagePublishingHistory`.
        """

#
# Binary package publishing
#

class IBinaryPackageFilePublishing(IFilePublishing):
    """Binary package files and their publishing status"""
    # Note that it is really /source/ package name below, and not a
    # thinko; at least, that's what Celso tells me the code uses
    #   -- kiko, 2006-03-22
    sourcepackagename = TextLine(
            title=_('Source package name'), required=True, readonly=True,
            )
    binarypackagepublishing = Int(
            title=_('Binary Package publishing record id'), required=True,
            readonly=True,
            )
    architecturetag = TextLine(
            title=_("Architecture tag. As per dpkg's use"), required=True,
            readonly=True,
            )


class ISecureBinaryPackagePublishingHistory(IPublishing):
    """A binary package publishing record."""
    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    binarypackagerelease = Int(
            title=_('The binary package being published'), required=False,
            readonly=False,
            )
    distroarchseries = Int(
            title=_('The distroarchseries being published into'),
            required=False, readonly=False,
            )
    component = Int(
            title=_('The component being published into'),
            required=False, readonly=False,
            )
    section = Int(
            title=_('The section being published into'),
            required=False, readonly=False,
            )
    priority = Int(
            title=_('The priority being published into'),
            required=False, readonly=False,
            )
    datepublished = Datetime(
            title=_('The date on which this record was published'),
            required=False, readonly=False,
            )
    scheduleddeletiondate = Datetime(
            title=_('The date on which this record is scheduled for '
                    'deletion'),
            required=False, readonly=False,
            )
    status = Int(
            title=_('The status of this publishing record'),
            required=False, readonly=False,
            )
    pocket = Int(
            title=_('The pocket into which this entry is published'),
            required=True, readonly=True,
            )
    supersededby = Int(
            title=_('The build which superseded this one'),
            required=False, readonly=False,
            )
    datecreated = Datetime(
            title=_('The date on which this record was created'),
            required=True, readonly=False,
            )
    datesuperseded = Datetime(
            title=_('The date on which this record was marked superseded'),
            required=False, readonly=False,
            )
    datemadepending = Datetime(
            title=_('The date on which this record was set as pending '
                    'removal'),
            required=False, readonly=False,
            )
    dateremoved = Datetime(
            title=_('The date on which this record was removed from the '
                    'published set'),
            required=False, readonly=False,
            )
    archive = Int(
            title=_('Archive ID'), required=True, readonly=True,
            )
    embargo = Bool(
            title=_('Whether or not this record is under embargo'),
            required=True, readonly=False,
            )
    embargolifted = Datetime(
            title=_('The date and time at which this record had its '
                    'embargo lifted'),
            required=False, readonly=False,
            )
    removed_by = Int(
        title=_('The IPerson responsible for the removal'),
        required=False, readonly=False,
        )
    removal_comment = Text(
        title=_('Reason why this publication is going to be removed.'),
        required=False, readonly=False,
        )


class IBinaryPackagePublishingHistory(ISecureBinaryPackagePublishingHistory):
    """A binary package publishing record."""

    distroarchseriesbinarypackagerelease = Attribute("The object that "
        "represents this binarypacakgerelease in this distroarchseries.")

    def changeOverride(new_component=None, new_section=None,
                       new_priority=None):
        """Change the component, section and/or priority of this publication.

        It is changed only if the argument is not None.

        Return the overridden publishing record, either a
        `ISourcePackagePublishingHistory` or `IBinaryPackagePublishingHistory`.
        """


class PackagePublishingStatus(DBEnumeratedType):
    """Package Publishing Status

     A package has various levels of being published within a DistroSeries.
     This is important because of how new source uploads dominate binary
     uploads bit-by-bit. Packages (source or binary) enter the publishing
     tables as 'Pending', progress through to 'Published' eventually become
     'Superseded' and then become 'PendingRemoval'. Once removed from the
     DistroSeries the publishing record is also removed.
     """

    PENDING = DBItem(1, """
        Pending

        This [source] package has been accepted into the DistroSeries and
        is now pending the addition of the files to the published disk area.
        In due course, this source package will be published.
        """)

    PUBLISHED = DBItem(2, """
        Published

        This package is currently published as part of the archive for that
        distroseries. In general there will only ever be one version of any
        source/binary package published at any one time. Once a newer
        version becomes published the older version is marked as superseded.
        """)

    SUPERSEDED = DBItem(3, """
        Superseded

        When a newer version of a [source] package is published the existing
        one is marked as "superseded".  """)

    DELETED = DBItem(4, """
        Deleted

        When a publication was "deleted" from the archive by user request.
        Records in this state contain a reference to the Launchpad user
        responsible for the deletion and a text comment with the removal
        reason.
        """)

    OBSOLETE = DBItem(5, """
        Obsolete

        When a distroseries becomes obsolete, its published packages
        are no longer required in the archive.  The publications for
        those packages are marked as "obsolete" and are subsequently
        removed during domination and death row processing.
        """)


class PackagePublishingPriority(DBEnumeratedType):
    """Package Publishing Priority

    Binary packages have a priority which is related to how important
    it is to have that package installed in a system. Common priorities
    range from required to optional and various others are available.
    """

    REQUIRED = DBItem(50, """
        Required

        This priority indicates that the package is required. This priority
        is likely to be hard-coded into various package tools. Without all
        the packages at this priority it may become impossible to use dpkg.
        """)

    IMPORTANT = DBItem(40, """
        Important

        If foo is in a package; and "What is going on?! Where on earth is
        foo?!?!" would be the reaction of an experienced UNIX hacker were
        the package not installed, then the package is important.
        """)

    STANDARD = DBItem(30, """
        Standard

        Packages at this priority are standard ones you can rely on to be in
        a distribution. They will be installed by default and provide a
        basic character-interface userland.
        """)

    OPTIONAL = DBItem(20, """
        Optional

        This is the software you might reasonably want to install if you did
        not know what it was or what your requiredments were. Systems such
        as X or TeX will live here.
        """)

    EXTRA = DBItem(10, """
        Extra

        This contains all the packages which conflict with those at the
        other priority levels; or packages which are only useful to people
        who have very specialised needs.
        """)


class PackagePublishingPocket(DBEnumeratedType):
    """Package Publishing Pocket

    A single distroseries can at its heart be more than one logical
    distroseries as the tools would see it. For example there may be a
    distroseries called 'hoary' and a SECURITY pocket subset of that would
    be referred to as 'hoary-security' by the publisher and the distro side
    tools.
    """

    RELEASE = DBItem(0, """
        Release

        The package versions that were published
        when the distribution release was made.
        For releases that are still under development,
        packages are published here only.
        """)

    SECURITY = DBItem(10, """
        Security

        Package versions containing security fixes for the released
        distribution.
        It is a good idea to have security updates turned on for your system.
        """)

    UPDATES = DBItem(20, """
        Updates

        Package versions including new features after the distribution
        release has been made.
        Updates are usually turned on by default after a fresh install.
        """)

    PROPOSED = DBItem(30, """
        Proposed

        Package versions including new functions that should be widely
        tested, but that are not yet part of a default installation.
        People who "live on the edge" will test these packages before they
        are accepted for use in "Updates".
        """)

    BACKPORTS = DBItem(40, """
        Backports

        Backported packages.
        """)

pocketsuffix = {
    PackagePublishingPocket.RELEASE: "",
    PackagePublishingPocket.SECURITY: "-security",
    PackagePublishingPocket.UPDATES: "-updates",
    PackagePublishingPocket.PROPOSED: "-proposed",
    PackagePublishingPocket.BACKPORTS: "-backports",
}
