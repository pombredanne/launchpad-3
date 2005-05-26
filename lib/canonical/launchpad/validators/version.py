# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

def valid_version(name):
    """validate a version number

    Note that this is more flexible than the Debian naming policy,
    as it states 'SHOULD' rather than 'MUST', and we have already
    imported packages that don't match it. Note that versions
    may contain both uppercase and lowercase letters so we shouldn't use them
    in URLs. Also note that both a product name and a version may contain
    hypens, so we cannot join the product name and the version with a hypen
    to form a unique string (we need to use a space or some other character
    disallowed in the product name spec instead.
    """
    import re
    pat = r"^[A-Za-z0-9\\+:\\.\\-\\~]+$"
    if name is None or re.match(pat, name):
        return True
    return False
    
valid_version.sql_signature = [
    ('name', 'text'),
    ]

