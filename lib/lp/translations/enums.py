# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enumerations used in the lp/translations modules."""

__metaclass__ = type
__all__ = [
    'RosettaImportStatus',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )


class RosettaImportStatus(DBEnumeratedType):
    """Rosetta Import Status

    Define the status of an import on the Import queue. It could have one
    of the following states: approved, imported, deleted, failed, needs_review
    or blocked.
    """

    APPROVED = DBItem(1, """
        Approved

        The entry has been approved by a Rosetta Expert or was able to be
        approved by our automatic system and is waiting to be imported.
        """)

    IMPORTED = DBItem(2, """
        Imported

        The entry has been imported.
        """)

    DELETED = DBItem(3, """
        Deleted

        The entry has been removed before being imported.
        """)

    FAILED = DBItem(4, """
        Failed

        The entry import failed.
        """)

    NEEDS_REVIEW = DBItem(5, """
        Needs Review

        A Rosetta Expert needs to review this entry to decide whether it will
        be imported and where it should be imported.
        """)

    BLOCKED = DBItem(6, """
        Blocked

        The entry has been blocked to be imported by a Rosetta Expert.
        """)

    NEEDS_INFORMATION = DBItem(7, """
        Needs Information

        The reviewer needs more information before this entry can be approved.
        """)
