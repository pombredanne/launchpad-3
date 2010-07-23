# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Constants that refer to values in sampledata.

If ever you use a literal in a test that refers to sample data, even if it's
just a small number, then you should define it as a constant here.
"""

__metaclass__ = type
__all__ = [
    'NO_PRIVILEGE_EMAIL',
    ]


ADMIN_EMAIL = 'foo.bar@canonical.com'
NO_PRIVILEGE_EMAIL = 'no-priv@canonical.com'
USER_EMAIL = 'test@canonical.com'
VCS_IMPORTS_MEMBER_EMAIL = 'david.allouche@canonical.com'
