# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Queue interfaces."""

__metaclass__ = type

__all__ = [
    'QueueStateWriteProtectedError',
    'QueueInconsistentStateError',
    'QueueSourceAcceptError',
    'QueueBuildAcceptError',
    'IDistroReleaseQueue',
    'IDistroReleaseQueueBuild',
    'IDistroReleaseQueueSource',
    'IDistroReleaseQueueCustom',
    'IDistroReleaseQueueSet',
    ]

from zope.schema import Int
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')


class QueueStateWriteProtectedError(Exception):
    """This exception prevent directly set operation in queue state.

    The queue state machine is controlled by its specific provided methods,
    like: set_new, set_accepted and so on.
    """


class QueueInconsistentStateError(Exception):
    """Queue state machine error.

    It's generate when the solicited state makes the record inconsistent
    against the current system constraints.
    """


class QueueSourceAcceptError(Exception):
    """It prevents a DistroReleaseQueueSource from being ACCEPTED.

    It is generated by Component and/or Section mismatching in a DistroRelease.
    """

class QueueBuildAcceptError(Exception):
    """It prevents a DistroReleaseQueueBuild from being ACCEPTED.

    It is generated by Component and/or Section mismatching in a DistroRelease.
    """


class IDistroReleaseQueue(Interface):
    """A Queue item for Lucille"""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )

    status = Int(
            title=_("Read-only Queue status"), required=False, readonly=True,
            )

    distrorelease = Int(
            title=_("Distribution release"), required=True, readonly=False,
            )

    pocket = Int(
            title=_("The pocket"), required=True, readonly=False,
            )

    changesfile = Attribute("The librarian alias for the changes file "
                            "associated with this upload")
    changesfilename = Attribute("The filename of the changes file.")

    sources = Attribute("The queue sources associated with this queue item")
    builds = Attribute("The queue builds associated with the queue item")

    datecreated = Attribute("The date on which this queue was created.")

    sourcepackagename = Attribute("The source package name for this item.")

    sourceversion = Attribute("The source package version for this item")

    age = Attribute("The age of this queue item. (now - datecreated)")

    def set_new():
        """Set Queue state machine to NEW."""

    def set_unapproved():
        """Set Queue state machine to UNAPPROVED."""

    def set_accepted():
        """Set Queue state machine to ACCEPTED.

        Preform the required checks on its content, so we garantee data
        integrity by code.
        """

    def set_done():
        """Set Queue state machine to DONE."""

    def set_rejected():
        """Set Queue state machine to REJECTED."""

    def realiseUpload(logger=None):
        """Take this ACCEPTED upload and create the publishing records for it
        as appropriate.

        When derivation is taken into account, this may result in queue items
        being created for derived distributions.

        If a logger is provided, messages will be written to it as the upload
        is entered into the publishing records.
        """

    def addSource(spr):
        """Add the provided source package release to this queue entry."""

    def addBuild(build):
        """Add the provided build to this queue entry."""

    def addCustom(library_file, custom_type):
        """Add the provided library file alias as a custom queue entry of
        the given custom type.
        """


class IDistroReleaseQueueBuild(Interface):
    """A Queue item's related builds (for Lucille)"""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )


    distroreleasequeue = Int(
            title=_("Distribution release queue"), required=True,
            readonly=False,
            )

    build = Int(
            title=_("The related build"), required=True, readonly=False,
            )

    def publish(logger=None):
        """Publish this queued source in the distrorelease referred to by
        the parent queue item.

        We determine the distroarchrelease by matching architecturetags against
        the distroarchrelease the build was compiled for.

        This method can raise NotFoundError if the architecturetag can't be
        matched up in the queue item's distrorelease.

        Returns a list of the secure binary package publishing history
        objects in case it is of use to the caller. This may include records
        published into other distroarchreleases if this build contained arch
        independant packages.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """

class IDistroReleaseQueueSource(Interface):
    """A Queue item's related sourcepackagereleases (for Lucille)"""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )


    distroreleasequeue = Int(
            title=_("Distribution release queue"), required=True,
            readonly=False,
            )

    sourcepackagerelease = Int(
            title=_("The related source package release"), required=True,
            readonly=False,
            )
    def checkComponentAndSection():
        """Verify the current Component and Section via Selection table.

        Check if the current sourcepackagerelease component and section
        matches with those included in the target distribution release,
        if not raise QueueSourceAcceptError exception.
        """

    def publish(logger=None):
        """Publish this queued source in the distrorelease referred to by
        the parent queue item.

        Returns the secure source package publishing history object in case
        it is of use to the caller.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """


class IDistroReleaseQueueCustom(Interface):
    """A Queue item's related custom format files (for uploader/queue)"""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )

    distroreleasequeue = Int(
            title=_("Distribution release queue"), required=True,
            readonly=False,
            )

    customformat = Int(
            title=_("The custom format for the file"), required=True,
            readonly=False,
            )

    libraryfilealias = Int(
            title=_("The file"), required=True, readonly=False,
            )

    def publish(logger=None):
        """Publish this custom item directly into the filesystem.

        This can only be run by a process which has filesystem access to
        the archive (or wherever else the content will go).

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """

    def publish_DEBIAN_INSTALLER(logger=None):
        """Publish this custom item as a raw installer tarball.

        This will write the installer tarball out to the right part of
        the archive.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """

    def publish_ROSETTA_TRANSLATIONS(logger=None):
        """Publish this custom item as a rosetta tarball.

        Essentially this imports the tarball into rosetta.

        If a logger is provided, information pertaining to the publishing
        process will be logged to it.
        """

class IDistroReleaseQueueSet(Interface):
    """Set methods for IDistroReleaseQueue"""

    def __iter__():
        """IDistroReleaseQueue iterator"""

    def __getitem__(queue_id):
        """Retrieve an IDistroReleaseQueue by a given id"""

    def get(queue_id):
        """Retrieve an IDistroReleaseQueue by a given id"""

    def count(self, status=None, distrorelease=None):
        """Number of IDistroReleaseQueue present in a given status.

        If status is ommitted return the number of all entries.
        'distrorelease' is optional and restrict the results in given
        distrorelease.
        """
