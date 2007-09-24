# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Publishing interfaces."""

__metaclass__ = type

__all__ = [
    'ISourcePackageFilePublishing',
    'IBinaryPackageFilePublishing',
    'ISecureSourcePackagePublishingHistory',
    'ISecureBinaryPackagePublishingHistory',
    'ISourcePackagePublishingHistory',
    'IBinaryPackagePublishingHistory',
    'IPublishing',
    'IArchivePublisher',
    'IArchiveFilePublisher',
    'IArchiveSafePublisher',
    'NotInPool',
    'PoolFileOverwriteError',
    'pocketsuffix'
    ]

from zope.schema import Bool, Datetime, Int, TextLine
from zope.interface import Interface, Attribute

from canonical.launchpad import _
from canonical.lp.dbschema import PackagePublishingPocket

pocketsuffix = {
    PackagePublishingPocket.RELEASE: "",
    PackagePublishingPocket.SECURITY: "-security",
    PackagePublishingPocket.UPDATES: "-updates",
    PackagePublishingPocket.PROPOSED: "-proposed",
    PackagePublishingPocket.BACKPORTS: "-backports",
}

#
# Archive Publisher API and Exceptions
#

class IPublishing(Interface):
    """Ability to publish associated publishing records."""

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

class IArchivePublisher(Interface):
    """Ability to publish a publishing record."""

    files = Attribute("Files included in this publication.")
    secure_record = Attribute("Correspondent secure package history record.")

    def publish(diskpool, log):
        """Publish or ensure contents of this publish record

        Skip records which attempt to overwrite the archive (same file paths
        with different content) and do not update the database.

        If all the files get published correctly update its status properly.
        """

    def getIndexStanza():
        """Return respective archive index stanza contents

        It's based on the locally provided buildIndexStanzaTemplate method,
        which differs for binary and source instances.
        """

    def buildIndexStanzaFields():
        """Build a map of fields and values to be in the Index file.

        The fields and values ae mapped into a dictionary, where the key is
        the field name and value is the value string.
        """


class IArchiveFilePublisher(Interface):
    """Ability to publish and archive file"""

    publishing_record = Attribute(
        "Return the respective Source or Binary publishing record "
        "(in the form of I{Source,Binary}PackagePublishingHistory).")

    def publish(diskpool, log):
        """Publish or ensure contents of this file in the archive.

        Create symbolic link to files already present in different component
        or add file from librarian if it's not present. Update the database
        to represent the current archive state.
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
# Source package publishing
#

class IBaseSourcePackagePublishing(Interface):
    distribution = Int(
            title=_('Distribution ID'), required=True, readonly=True,
            )
    distroseriesname = TextLine(
            title=_('Series name'), required=True, readonly=True,
            )
    sourcepackagename = TextLine(
            title=_('Binary package name'), required=True, readonly=True,
            )
    componentname = TextLine(
            title=_('Component name'), required=True, readonly=True,
            )
    publishingstatus = Int(
            title=_('Package publishing status'), required=True, readonly=True,
            )
    pocket = Int(
            title=_('Package publishing pocket'), required=True, readonly=True,
            )
    archive = Int(
            title=_('Archive ID'), required=True, readonly=True,
            )


class ISourcePackageFilePublishing(IBaseSourcePackagePublishing):
    """Source package release files and their publishing status"""
    sourcepackagepublishing = Int(
            title=_('Sourcepackage publishing record id'), required=True,
            readonly=True,
            )
    libraryfilealias = Int(
            title=_('Sourcepackage release file alias'), required=True,
            readonly=True,
            )
    libraryfilealiasfilename = TextLine(
            title=_('File name'), required=True, readonly=True,
            )


class ISourcePackagePublishingBase(Interface):
    """Base class for ISourcePackagePublishing, without extra properties."""
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
            title=_('The date on which this record is scheduled for deletion'),
            required=False, readonly=False,
            )
    pocket = Int(
            title=_('The pocket into which this entry is published'),
            required=True, readonly=True,
            )
    archive = Int(
            title=_('Archive ID'), required=True, readonly=True,
            )


class IExtendedSourcePackagePublishing(ISourcePackagePublishingBase):
    """Base class with extra attributes for ISSPPH."""
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
            title=_('The date on which this record was set as pending removal'),
            required=False, readonly=False,
            )
    dateremoved = Datetime(
            title=_('The date on which this record was removed from the '
                    'published set'),
            required=False, readonly=False,
            )


class ISecureSourcePackagePublishingHistory(IExtendedSourcePackagePublishing):
    """A source package publishing history record."""
    embargo = Bool(
            title=_('Whether or not this record is under embargo'),
            required=True, readonly=False,
            )
    embargolifted = Datetime(
            title=_('The date on which this record had its embargo lifted'),
            required=False, readonly=False,
            )


class ISourcePackagePublishingHistory(IExtendedSourcePackagePublishing):
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

    def publishedBinaries():
        """Return all resulted IBinaryPackagePublishingHistory.

        Follow the build record and return every PUBLISHED binary publishing
        record for DistroArchSeriess in this DistroSeries, ordered by
        architecturetag.
        """


#
# Binary package publishing
#


class IBaseBinaryPackagePublishing(Interface):
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
            title=_('Package publishing status'), required=True, readonly=True,
            )
    pocket = Int(
            title=_('Package publishing pocket'), required=True, readonly=True,
            )
    archive = Int(
            title=_('Archive ID'), required=True, readonly=True,
            )


class IBinaryPackageFilePublishing(IBaseBinaryPackagePublishing):
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
    libraryfilealias = Int(
            title=_('Binarypackage file alias'), required=True,
            readonly=True,
            )
    libraryfilealiasfilename = TextLine(
            title=_('File name'), required=True, readonly=True,
            )
    architecturetag = TextLine(
            title=_("Architecture tag. As per dpkg's use"), required=True,
            readonly=True,
            )


class IExtendedBinaryPackagePublishing(Interface):
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
            title=_('The date on which this record is scheduled for deletion'),
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
            title=_('The date on which this record was set as pending removal'),
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


class ISecureBinaryPackagePublishingHistory(IExtendedBinaryPackagePublishing):
    """A binary package publishing record."""
    embargo = Bool(
            title=_('Whether or not this record is under embargo'),
            required=True, readonly=False,
            )
    embargolifted = Datetime(
            title=_('The date and time at which this record had its '
                    'embargo lifted'),
            required=False, readonly=False,
            )


class IBinaryPackagePublishingHistory(IExtendedBinaryPackagePublishing):
    """A binary package publishing record."""

    distroarchseriesbinarypackagerelease = Attribute("The object that "
        "represents this binarypacakgerelease in this distroarchseries.")

    hasRemovalRequested = Bool(
            title=_('Whether a removal has been requested for this record')
            )
