# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Validators for the .name attribute (defined in various schemas.)"""

__metaclass__ = type

import re

from zope.schema import ValidationError

from canonical.launchpad import _

def valid_name(name):
    pat = r"^[a-z0-9][a-z0-9\\+\\.\\-]+$"
    if re.match(pat, name):
        return True
    return False

class InvalidName(ValidationError):
    __doc__ = _(
            "Invalid input. names must start with a letter or "
            "number and be lowercase. The characers '+', '-' and '.' "
            "are also allowed after the first character."
            )

def name_validator(name):
    if not valid_name(name):
        raise InvalidName(name)
    return True

valid_name.sql_signature = [('name', 'text')]

