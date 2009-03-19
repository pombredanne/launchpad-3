# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Validator for SourceForge project name."""

__metaclass__ = type
__all__ = [
    'sourceforge_project_name_validator',
    'valid_sourceforge_project_name',
    ]

import re

from textwrap import dedent

from canonical.launchpad import _
from canonical.launchpad.validators import LaunchpadValidationError


# This is based on the definition of <label> in RFC 1035, section
# 2.3.1, which is what SourceForge project names are based on.
re_valid_rfc1035_label = re.compile(
    '^[a-zA-Z](?:[a-zA-Z0-9-]{,61}[a-zA-Z0-9])?$')


def valid_sourceforge_project_name(project_name):
    """Is this is a valid SourceForge project name?

    Project names must be valid domain name components.

        >>> valid_sourceforge_project_name('mailman')
        True

        >>> valid_sourceforge_project_name('hop-2-hop')
        True

        >>> valid_sourceforge_project_name('quake3')
        True

    They cannot start with a number.

        >>> valid_sourceforge_project_name('1mailman')
        False

    Nor can they start or end with a hyphen.

        >>> valid_sourceforge_project_name('-mailman')
        False

        >>> valid_sourceforge_project_name('mailman-')
        False

    They must be between 1 and 63 characters in length.

        >>> valid_sourceforge_project_name('x' * 0)
        False

        >>> valid_sourceforge_project_name('x' * 1)
        True

        >>> valid_sourceforge_project_name('x' * 63)
        True

        >>> valid_sourceforge_project_name('x' * 64)
        False

    """
    return re_valid_rfc1035_label.match(project_name) is not None


def sourceforge_project_name_validator(project_name):
    """Raise a validation exception if the name is not valid.

        >>> sourceforge_project_name_validator('valid')
        True

        >>> sourceforge_project_name_validator(
        ...     '1nvalid') #doctest: +ELLIPSIS,+NORMALIZE_WHITESPACE
        Traceback (most recent call last):
        ...
        LaunchpadValidationError: SourceForge project names...
    """
    if valid_sourceforge_project_name(project_name):
        return True
    else:
        raise LaunchpadValidationError(
            _(dedent("""
                SourceForge project names must begin with a letter (A
                to Z; case does not matter), followed by zero or more
                letters, numbers, or hyphens, then end with a letter
                or number. In total it must not be more than 63
                characters in length.""")))
