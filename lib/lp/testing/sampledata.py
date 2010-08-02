# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Constants that refer to values in sampledata.

If ever you use a literal in a test that refers to sample data, even if it's
just a small number, then you should define it as a constant here.
"""

__metaclass__ = type
__all__ = [
    'COMMERCIAL_ADMIN_EMAIL',
    'NO_PRIVILEGE_EMAIL',
    ]


NO_PRIVILEGE_EMAIL = 'no-priv@canonical.com'
COMMERCIAL_ADMIN_EMAIL = 'commercial-member@canonical.com'
