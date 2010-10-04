# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'TeamMembershipTransitionError',
    ]

import httplib

from lazr.restful.declarations import webservice_error


class TeamMembershipTransitionError(ValueError):
    """Indicates something has gone wrong with the transtiion.

    Generally, this indicates a bad transition (e.g. approved to proposed)
    or an invalid transition (e.g. unicorn).
    """
    webservice_error(httplib.BAD_REQUEST)
