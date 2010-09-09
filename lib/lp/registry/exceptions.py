# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Exceptions for the Registry app."""

__metaclass__ = type
__all__ = [
    'NotADerivedSeriesError',
    ]


class NotADerivedSeriesError(Exception):
    """A distro series difference must be created with a derived series.

    This is raised when a DistroSeriesDifference is created with a
    non-derived series - that is, a distroseries with a null Parent."""

