# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""GPG validators"""

__metaclass__ = type

import re


def valid_fingerprint(fingerprint):
    # Fingerprints of v3 keys are md5, fingerprints of v4 keys are sha1;
    # accordingly, fingerprints of v3 keys are 128 bit, those of v4 keys
    # 160. Check therefore for strings of hex characters that are 32
    # (4 * 32 == 128) or 40 characters long (4 * 40 = 160).
    if len(fingerprint) not in (32, 40):
        return False
    if re.match(r"^[\dA-F]+$", fingerprint) is None:
        return False
    return True


def valid_keyid(keyid):
    if re.match(r"^[\dA-F]{8}$", keyid) is not None:
        return True
    else:
        return False

