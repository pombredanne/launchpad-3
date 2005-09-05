# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Validators for the .name attribute (defined in various schemas.)"""

__metaclass__ = type

import re
from textwrap import dedent

from zope.schema import ValidationError

from canonical.launchpad import _
from canonical.launchpad.validators import LaunchpadValidationError

from zope.schema import ValidationError

from canonical.launchpad import _

def valid_name(name):
    """Return True if the name is valid, otherwise False.

    Lauchpad `name` attributes are designed for use as url components
    and short unique identifiers to things.

    The default name constraints may be too strict for some objects,
    such as binary packages or arch branches where naming conventions already
    exists, so they may use their own specialized name validators
    """
    pat = r"^[a-z0-9][a-z0-9\+\.\-]+$"
    if re.match(pat, name):
        return True
    return False

def name_validator(name):
    """Return True if the name is valid, or raise a LaunchpadValidationError"""
    if not valid_name(name):
        raise LaunchpadValidationError(_(dedent("""
            Invalid name '%s'. names must start with a letter or
            number and be lowercase. The characers <kbd>+</kbd>,
            <kbd>-</kbd> and <kbd>.</kbd> are also allowed after the
            first character.
            """)), name)
    return True

