# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Validators for the clean-username (`Person.name`) attribute."""

__metaclass__ = type

import re
from textwrap import dedent

from lp import _
from lp.app.validators import LaunchpadValidationError
from lp.services.webapp.escaping import (
    html_escape,
    structured,
    )


username_valid_pattern = re.compile(r"^[a-z0-9](-?[a-z0-9])+$")
username_blocked_pattern = re.compile(r"^[0-9-]+$")
username_invalid_pattern = re.compile(r"^[^a-z0-9]+|[^a-z0-9-]+|[^a-z0-9]$")


def sanitize_username(username):
    """Remove from the given username all characters that are not allowed.

    The characters not allowed in Launchpad usernames are described by
    `username_invalid_pattern`.

    >>> sanitize_username('foo_bar')
    'foobar'
    >>> sanitize_username('foo.bar+baz')
    'foobarbaz'
    >>> sanitize_username('-#foo -$fd?.0+-')
    'foo-fd0'

    """
    return username_invalid_pattern.sub('', username)


def valid_username(username):
    """Return True if the username is valid, otherwise False.

    Launchpad `username` (`Person.name`) attribute is designed to serve as
    an human-friendly identifier to a identity across multiple services.

    >>> valid_username('hello')
    True
    >>> valid_username('helLo')
    False
    >>> valid_username('hel|o')
    False
    >>> valid_username('hel.o')
    False
    >>> valid_username('hel+o')
    False
    >>> valid_username('he')
    False
    >>> valid_username('hel')
    True
    >>> valid_username('h' * 32)
    True
    >>> valid_username('h' * 33)
    False
    >>> valid_username('-he')
    False
    >>> valid_username('he-')
    False

    """
    if not username_valid_pattern.match(username):
        return False

    length = len(username)
    if length < 3 or length > 32:
        return False

    if username_blocked_pattern.match(username):
        return False

    return True


def username_validator(username):
    """Return True if the username is valid, or raise a
    LaunchpadValidationError.
    """
    if not valid_username(username):
        message = _(dedent("""
            Invalid username '${username}'. Usernames must be at least three
            and no longer than 32 characters long. They must contain at least
            one letter, start and end with a letter or number. All letters
            must be lower-case and non-consecutive hyphens are allowed."""),
        mapping={'username': html_escape(username)})
        raise LaunchpadValidationError(structured(message))

    return True
