# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""GPG validators"""

__metaclass__ = type

def valid_fingerprint(fingerprint):
    import re
    if re.match(r"[\dA-F]{40}", fingerprint) is not None:
        return True
    else:
        return False
valid_fingerprint.sql_signature = [('fingerprint', 'text')]

def valid_keyid(keyid):
    import re
    if re.match(r"[\dA-F]{8}", keyid) is not None:
        return True
    else:
        return False
valid_keyid.sql_signature = [('keyid', 'text')]
