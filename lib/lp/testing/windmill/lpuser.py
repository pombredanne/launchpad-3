# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for Windmill tests written in Python."""

__metaclass__ = type
__all__ = []

import windmill


def get_basic_login_url(email, password):
    """Return the constructed url to login a user."""
    base_url = windmill.settings['TEST_URL']
    basic_auth_url = base_url.replace('http://', 'http://%s:%s@')
    basic_auth_url = basic_auth_url + '+basiclogin'
    return basic_auth_url % (email, password)


class LaunchpadUser:
    """Object representing well-known user on Launchpad."""

    def __init__(self, display_name, email, password):
        self.display_name = display_name
        self.email = email
        self.password = password


# Well Known Users
SAMPLE_PERSON = LaunchpadUser(
    'Sample Person', 'test@canonical.com', 'test')

FOO_BAR = LaunchpadUser(
    'Foo Bar', 'foo.bar@canonical.com', 'test')

NO_PRIV = LaunchpadUser(
    'No Privileges User', 'no-priv@canonical.com', 'test')

TRANSLATIONS_ADMIN = LaunchpadUser(
    u'Carlos Perell\xf3 Mar\xedn', 'carlos@canonical.com', 'test')
