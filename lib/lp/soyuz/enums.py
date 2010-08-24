# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enumerations used in the lp/soyuz modules."""

__metaclass__ = type
__all__ = [
    'ArchiveJobType',
    'ArchivePermissionType',
    'ArchivePurpose',
    'ArchiveStatus',
    'ArchiveSubscriberStatus',
    'BinaryPackageFileType',
    'BinaryPackageFormat',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    EnumeratedType,
    Item,
    use_template,
    )


class ArchiveJobType(DBEnumeratedType):
    """Values that IArchiveJob.job_type can take."""

    COPY_ARCHIVE = DBItem(0, """
        Create a copy archive.

        This job creates a copy archive from the current state of
        the archive.
        """)


class ArchivePermissionType(DBEnumeratedType):
    """Archive Permission Type.

    The permission being granted, such as upload rights, or queue
    manipulation rights.
    """

    UPLOAD = DBItem(1, """
        Archive Upload Rights

        This permission allows a user to upload.
        """)

    QUEUE_ADMIN = DBItem(2, """
        Queue Administration Rights

        This permission allows a user to administer the distroseries
        upload queue.
        """)


class ArchivePurpose(DBEnumeratedType):
    """The purpose, or type, of an archive.

    A distribution can be associated with different archives and this
    schema item enumerates the different archive types and their purpose.

    For example, Partner/ISV software in ubuntu is stored in a separate
    archive. PPAs are separate archives and contain packages that 'overlay'
    the ubuntu PRIMARY archive.
    """

    PRIMARY = DBItem(1, """
        Primary Archive

        This is the primary Ubuntu archive.
        """)

    PPA = DBItem(2, """
        PPA Archive

        This is a Personal Package Archive.
        """)

    PARTNER = DBItem(4, """
        Partner Archive

        This is the archive for partner packages.
        """)

    COPY = DBItem(6, """
        Generalized copy archive

        This kind of archive will be used for rebuilds, snapshots etc.
        """)

    DEBUG = DBItem(7, """
        Debug Archive

        This kind of archive will be user for publishing package with
        debug-symbols.
        """)


class ArchiveStatus(DBEnumeratedType):
    """The status of an archive, e.g. active, disabled. """

    ACTIVE = DBItem(0, """
        Active

        This archive accepts uploads, copying and publishes packages.
        """)

    DELETING = DBItem(1, """
        Deleting

        This archive is in the process of being deleted.  This is a user-
        requested and short-lived status.
        """)

    DELETED = DBItem(2, """
        Deleted

        This archive has been deleted and removed from disk.
        """)


class ArchiveSubscriberStatus(DBEnumeratedType):
    """The status of an `ArchiveSubscriber`."""
    
    CURRENT = DBItem(1, """
        Active

        The subscription is current.
        """)
    
    EXPIRED = DBItem(2, """
        Expired

        The subscription has expired.
        """)
    
    CANCELLED = DBItem(3, """
        Cancelled

        The subscription was cancelled.
        """)


class BinaryPackageFileType(DBEnumeratedType):
    """Binary Package File Type

    Launchpad handles a variety of packaging systems and binary package
    formats. This schema documents the known binary package file types.
    """

    DEB = DBItem(1, """
        DEB Format

        This format is the standard package format used on Ubuntu and other
        similar operating systems.
        """)

    RPM = DBItem(2, """
        RPM Format

        This format is used on mandrake, Red Hat, Suse and other similar
        distributions.
        """)

    UDEB = DBItem(3, """
        UDEB Format

        This format is the standard package format used on Ubuntu and other
        similar operating systems for the installation system.
        """)

    DDEB = DBItem(4, """
        DDEB Format

        This format is the standard package format used on Ubuntu and other
        similar operating systems for distributing debug symbols.
        """)


class BinaryPackageFormat(DBEnumeratedType):
    """Binary Package Format

    Launchpad tracks a variety of binary package formats. This schema
    documents the list of binary package formats that are supported
    in Launchpad.
    """

    DEB = DBItem(1, """
        Ubuntu Package

        This is the binary package format used by Ubuntu and all similar
        distributions. It includes dependency information to allow the
        system to ensure it always has all the software installed to make
        any new package work correctly.  """)

    UDEB = DBItem(2, """
        Ubuntu Installer Package

        This is the binary package format used by the installer in Ubuntu and
        similar distributions.  """)

    EBUILD = DBItem(3, """
        Gentoo Ebuild Package

        This is the Gentoo binary package format. While Gentoo is primarily
        known for being a build-it-from-source-yourself kind of
        distribution, it is possible to exchange binary packages between
        Gentoo systems.  """)

    RPM = DBItem(4, """
        RPM Package

        This is the format used by Mandrake and other similar distributions.
        It does not include dependency tracking information.  """)

    DDEB = DBItem(5, """
        Ubuntu Debug Package

        This is the binary package format used for shipping debug symbols
        in Ubuntu and similar distributions.""")


