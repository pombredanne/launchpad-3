# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PrivatePersonLinkageError',
    'NameAlreadyTaken',
    'NoSuchDistroSeries',
    'UserCannotChangeMembershipSilently'
    'NoSuchSourcePackageName',
    ]

import httplib

from lazr.restful.declarations import webservice_error

from lp.app.errors import NameLookupFailed


class PrivatePersonLinkageError(ValueError):
    """An attempt was made to link a private person/team to something."""
    webservice_error(httplib.FORBIDDEN)

    
class NameAlreadyTaken(Exception):
    """The name given for a person is already in use by other person."""
    webservice_error(httplib.CONFLICT)


class NoSuchDistroSeries(NameLookupFailed):
    """Raised when we try to find a DistroSeries that doesn't exist."""
    webservice_error(httplib.BAD_REQUEST)
    _message_prefix = "No such distribution series"


class UserCannotChangeMembershipSilently(Unauthorized):
    """User not permitted to change membership status silently.

    Raised when a user tries to change someone's membership silently, and is
    not a Launchpad Administrator.
    """
    webservice_error(httplib.UNAUTHORIZED)


class NoSuchSourcePackageName(NameLookupFailed):
    """Raised when we can't find a particular sourcepackagename."""
    webservice_error(httplib.BAD_REQUEST)
    _message_prefix = "No such source package"
