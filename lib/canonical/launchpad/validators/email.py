# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""EmailAdress validator"""

__metaclass__ = type

import re


def valid_email(emailaddr):
    if re.match(r"^[_\.0-9a-zA-Z-+]+@([0-9a-zA-Z-]{1,}\.)*[a-zA-Z]{2,}$",
                emailaddr):
        return True
    else:
        return False
