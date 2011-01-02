# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enums for the Registry app."""

__metaclass__ = type
__all__ = [
    'PersonTransferJobType',
    'BugNotificationLevel',
    'DistroSeriesDifferenceStatus',
    'DistroSeriesDifferenceType',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )


class BugNotificationLevel(DBEnumeratedType):
    """Bug Notification Level.

    The type and volume of bug notification email sent to subscribers.
    """

    NOTHING = DBItem(10, """
        Nothing

        Don't send any notifications about bugs.
        """)

    LIFECYCLE = DBItem(20, """
        Lifecycle

        Only send a low volume of notifications about new bugs registered,
        bugs removed or bug targetting.
        """)

    METADATA = DBItem(30, """
        Details

        Send bug lifecycle notifications, as well as notifications about
        changes to the bug's details like status and description.
        """)

    COMMENTS = DBItem(40, """
        Discussion

        Send bug lifecycle notifications, detail change notifications and
        notifications about new events in the bugs's discussion, like new
        comments.
        """)


class DistroSeriesDifferenceStatus(DBEnumeratedType):
    """Distribution series difference status.

    The status of a package difference between two DistroSeries.
    """

    NEEDS_ATTENTION = DBItem(1, """
        Needs attention

        This difference is current and needs attention.
        """)

    BLACKLISTED_CURRENT = DBItem(2, """
        Blacklisted current version

        This difference is being ignored until a new package is uploaded
        or the status is manually updated.
        """)

    BLACKLISTED_ALWAYS = DBItem(3, """
        Blacklisted always

        This difference should always be ignored.
        """)

    RESOLVED = DBItem(4, """
        Resolved

        This difference has been resolved and versions are now equal.
        """)


class DistroSeriesDifferenceType(DBEnumeratedType):
    """Distribution series difference type."""

    UNIQUE_TO_DERIVED_SERIES = DBItem(1, """
        Unique to derived series

        This package is present in the derived series but not the parent
        series.
        """)

    MISSING_FROM_DERIVED_SERIES = DBItem(2, """
        Missing from derived series

        This package is present in the parent series but missing from the
        derived series.
        """)

    DIFFERENT_VERSIONS = DBItem(3, """
        Different versions

        This package is present in both series with different versions.
        """)


class PersonTransferJobType(DBEnumeratedType):
    """Values that IPersonTransferJob.job_type can take."""

    MEMBERSHIP_NOTIFICATION = DBItem(0, """
        Add-member notification

        Notify affected users of new team membership.
        """)
