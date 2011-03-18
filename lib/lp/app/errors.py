# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Cross application type errors for launchpad."""

__metaclass__ = type
__all__ = [
    'GoneError',
    'NameLookupFailed',
    'NotFoundError',
    'POSTToNonCanonicalURL',
    'TranslationUnavailable',
    'UnexpectedFormData',
    'UserCannotUnsubscribePerson',
    ]

from lazr.restful.declarations import error_status
from zope.security.interfaces import (
    ForbiddenAttribute,
    Unauthorized,
    )


class TranslationUnavailable(Exception):
    """Translation objects are unavailable."""


class NotFoundError(KeyError):
    """Launchpad object not found."""


class GoneError(KeyError):
    """Launchpad object is gone."""


class NameLookupFailed(NotFoundError):
    """Raised when a lookup by name fails.

    Subclasses should define the `_message_prefix` class variable, which will
    be prefixed to the quoted name of the name that could not be found.

    :ivar name: The name that could not be found.
    """

    _message_prefix = "Not found"

    def __init__(self, name, message=None):
        if message is None:
            message = self._message_prefix
        self.message = "%s: '%s'." % (message, name)
        self.name = name
        NotFoundError.__init__(self, self.message)

    def __str__(self):
        return self.message


class UnexpectedFormData(AssertionError):
    """Got form data that is not what is expected by a form handler."""


class POSTToNonCanonicalURL(UnexpectedFormData):
    """Got a POST to an incorrect URL.

    One example would be a URL containing uppercase letters.
    """

@error_status(401)
class UserCannotUnsubscribePerson(Unauthorized):
    """User does not have permission to unsubscribe person or team."""


# Slam a 401 response code onto all ForbiddenAttribute errors.
error_status(401)(ForbiddenAttribute)
