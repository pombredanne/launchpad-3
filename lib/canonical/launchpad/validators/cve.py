# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import re


def valid_cve(name):
    pat = r"^(19|20)\d\d-\d{4}$"
    if re.match(pat, name):
        return True
    return False

