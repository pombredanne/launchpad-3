# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Validators for the .name attribute (defined in various schemas.)"""

__metaclass__ = type

import re

def valid_name(name):
    pat = r"^[a-z0-9][a-z0-9\\+\\.\\-]+$"
    if re.match(pat, name):
        return True
    return False

valid_name.sql_signature = [('name', 'text')]

