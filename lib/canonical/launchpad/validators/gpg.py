# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""GPG validators"""

__metaclass__ = type

def valid_fingerprint(fingerprint):
    import re
    if re.match(r"[\dA-F]{40}", fingerprint) is not None:
        return True
    else:
        return False

def valid_keyid(keyid):
    import re
    if re.match(r"[\dA-F]{8}", keyid) is not None:
        return True
    else:
        return False
