# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

def valid_absolute_url(name):
    """validate an absolute URL.

    We define this as something that can be parsed into a URL that has both
    a protocol and a network address.
    """
    import re
    pat = r"^[A-Za-z0-9\\+:\\.\\-\\~]+$"
    if name is None or re.match(pat, name):
        return True
    return False
