# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enumerations used in the lp/soyuz modules."""

__metaclass__ = type
__all__ = [
    'ArchivePurpose',
    'ArchiveStatus',
    'ArchiveJobType',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    EnumeratedType,
    Item,
    use_template,
    )


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


class ArchiveJobType(DBEnumeratedType):
    """Values that IArchiveJob.job_type can take."""

    COPY_ARCHIVE = DBItem(0, """
        Create a copy archive.

        This job creates a copy archive from the current state of
        the archive.
        """)


