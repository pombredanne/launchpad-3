# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""EmailAdress validator"""

__metaclass__ = type

import re


def valid_email(emailaddr):
    """Validate an email address.

    >>> valid_email('kiko.async@hotmail.com')
    True
    >>> valid_email('kiko+async@hotmail.com')
    True
    >>> valid_email('kiko-async@hotmail.com')
    True
    >>> valid_email('kiko_async@hotmail.com')
    True
    >>> valid_email('kiko@async.com.br')
    True
    >>> valid_email('kiko@canonical.com')
    True
    >>> valid_email('i@tv')
    True

    As per OOPS-256D762:

    >>> valid_email('keith@risby-family.co.uk')
    True
    >>> valid_email('keith@risby-family-.co.uk')
    False
    >>> valid_email('keith@-risby-family.co.uk')
    False
    """
    email_re = r"^[_\.0-9a-zA-Z-+]+@(([0-9a-zA-Z-]{1,}\.)*)[a-zA-Z]{2,}$"
    email_match = re.match(email_re, emailaddr)
    if not email_match:
        return False
    host_minus_tld = email_match.group(1)
    if not host_minus_tld:
        return True
    for part in host_minus_tld.split("."):
        if part.startswith("-") or part.endswith("-"):
            return False
    return True

