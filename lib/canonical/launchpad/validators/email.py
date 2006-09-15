# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""EmailAdress validator"""

__metaclass__ = type

import re


def valid_email(emailaddr):
    """Validate an email address.

    >>> valid_email('kiko@canonical.com')
    True

    As per OOPS-256D762:

    >>> valid_email('keith@risby-family.co.uk')
    True
    >>> valid_email('keith@risby-family-.co.uk')
    False
    >>> valid_email('keith@-risby-family.co.uk')
    False
    """
    if re.match(r"^[_\.0-9a-zA-Z-+]+@[^-]([0-9a-zA-Z-]{1,}[^-]\.)*[a-zA-Z]{2,}$",
                emailaddr):
        return True
    else:
        return False

