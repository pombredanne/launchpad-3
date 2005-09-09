# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

def valid_cve(name):
    import re
    pat = r"^(19|20)\d\d-\d{4}$"
    if re.match(pat, name):
        return True
    return False
    
