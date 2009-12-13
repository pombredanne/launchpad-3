# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interfaces including common IDistroSeries and IProductSeries classes."""

__metaclass__ = type

__all__ = [
    'SeriesStatus'
    ]

from lazr.enum import DBEnumeratedType, DBItem

class SeriesStatus(DBEnumeratedType):
    """Distro/Product Series Status

    A Distro or Product series (warty, hoary, 1.4 for example) changes state
    throughout its development. This schema describes the level of
    development of the series.
    """

    EXPERIMENTAL = DBItem(1, """
        Experimental

        This series contains code that is far from active release planning or
        management.

        In the case of Ubuntu, series that are beyond the current
        "development" release will be marked as "experimental". We create
        those so that people have a place to upload code which is expected to
        be part of that distant future release, but which we do not want to
        interfere with the current development release.
        """)

    DEVELOPMENT = DBItem(2, """
        Active Development

        The series that is under active development.
        """)

    FROZEN = DBItem(3, """
        Pre-release Freeze

        When a series is near to release the administrators will freeze it,
        which typically means all changes require significant review before
        being accepted.
        """)

    CURRENT = DBItem(4, """
        Current Stable Release

        This is the latest stable release. Normally there will only
        be one of these for a given distribution.
        """)

    SUPPORTED = DBItem(5, """
        Supported

        This series is still supported, but it is no longer the current stable
        release.
        """)

    OBSOLETE = DBItem(6, """
        Obsolete

        This series is no longer supported, it is considered obsolete and
        should not be used on production systems.
        """)

    FUTURE = DBItem(7, """
        Future

        This is a future series of this product/distro in which the developers
        haven't started working yet.
        """)

