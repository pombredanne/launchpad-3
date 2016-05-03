# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Enumerations used in the lp/snappy modules."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'SnapStoreUploadStatus',
    ]

from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )


class SnapStoreUploadStatus(DBEnumeratedType):
    """Snap Store Upload Status

    Launchpad can optionally upload snap package builds to the store.  This
    enumeration tracks the status of such uploads.
    """

    PENDING = DBItem(1, """
        Pending

        This snap package will be uploaded to the store in due course.
        """)

    DONE = DBItem(2, """
        Done

        This snap package has been successfully uploaded to the store.
        """)

    FAILED = DBItem(3, """
        Failed

        Launchpad tried to upload this snap package to the store, but failed.
        """)
