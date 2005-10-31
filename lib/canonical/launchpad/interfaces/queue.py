# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Queue interfaces."""

__metaclass__ = type

__all__ = [
    'IDistroReleaseQueue',
    'IDistroReleaseQueueBuild',
    'IDistroReleaseQueueSource',
    'IDistroReleaseQueueCustom',
    ]

from zope.schema import Int
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IDistroReleaseQueue(Interface):
    """A Queue item for Lucille"""

    id = Int(
            title=_("ID"), required=True, readonly=True,
            )

    status = Int(
            title=_("Queue status"), required=True, readonly=False,
            )

    distrorelease = Int(
            title=_("Distribution release"), required=True, readonly=False,
            )

    pocket = Int(
            title=_("The pocket"), required=True, readonly=False,
            )

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
