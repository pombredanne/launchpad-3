# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities for Windmill tests written in Python."""

__metaclass__ = type
__all__ = []

import windmill

from canonical.launchpad.windmill.testing import constants


class LaunchpadUser:
    """Object representing well-known user on Launchpad."""

    def __init__(self, display_name, email, password):
        self.display_name = display_name
        self.email = email
        self.password = password

    def ensure_login(self, client):
        """Ensure that this user is logged on the page under windmill."""
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        lookup_user = (
            """lookupNode({xpath: '//div[@id="logincontrol"]//a'}).text""")
        result = client.commands.execJS(code=lookup_user)
        if (result['result'] is not None and
            result['result'].strip() == self.display_name):
            # We are logged in as that user already.
            return

        current_url = client.commands.execJS(
            code='windmill.testWin().location;')['result']['href']
        base_url = windmill.settings['TEST_URL']
        basic_auth_url = base_url.replace('http://', 'http://%s:%s@')
        basic_auth_url = basic_auth_url + '+basiclogin'
        client.open(url=basic_auth_url % (self.email, self.password))
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        client.open(url=current_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)


class AnonymousUser:
    """Object representing the anonymous user."""

    def ensure_login(self, client):
        """Ensure that the user is surfing anonymously."""
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        result = client.asserts.assertNode(
            link=u'Log in / Register', assertion=False)
        if result['result']:
            return

        # Open a page with invalid HTTP Basic Auth credentials just to
        # invalidate the ones previously used.
        current_url = client.commands.execJS(
            code='windmill.testWin().location;')['result']['href']
        current_url = current_url.replace('http://', 'http://foo:foo@')
        client.open(url=current_url)
        client.waits.forPageLoad(timeout=constants.PAGE_LOAD)


def login_person(person, password, client):
    """Create a LaunchpadUser for a person and password."""
    user = LaunchpadUser(
        person.displayname, person.preferredemail.email, password)
    user.ensure_login(client)


# Well Known Users
ANONYMOUS = AnonymousUser()

SAMPLE_PERSON = LaunchpadUser(
    'Sample Person', 'test@canonical.com', 'test')

FOO_BAR = LaunchpadUser(
    'Foo Bar', 'foo.bar@canonical.com', 'test')

NO_PRIV = LaunchpadUser(
    'No Privileges User', 'no-priv@canonical.com', 'test')

TRANSLATIONS_ADMIN = LaunchpadUser(
    u'Carlos Perell\xf3 Mar\xedn', 'carlos@canonical.com', 'test')
