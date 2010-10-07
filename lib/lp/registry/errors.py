# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'DistroSeriesDifferenceError',
    'NotADerivedSeriesError',
    'TeamMembershipTransitionError',
    ]

import httplib

from lazr.restful.declarations import webservice_error


class DistroSeriesDifferenceError(Exception):
    """Raised when package diffs cannot be created for a difference."""
    webservice_error(httplib.BAD_REQUEST)


class NotADerivedSeriesError(Exception):
    """A distro series difference must be created with a derived series.

    This is raised when a DistroSeriesDifference is created with a
    non-derived series - that is, a distroseries with a null Parent."""


class TeamMembershipTransitionError(ValueError):
    """Indicates something has gone wrong with the transtiion.

    Generally, this indicates a bad transition (e.g. approved to proposed)
    or an invalid transition (e.g. unicorn).
    """
    webservice_error(httplib.BAD_REQUEST)
