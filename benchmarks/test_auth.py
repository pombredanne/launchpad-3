# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Basic login to launchpad test."""

__metaclass__ = type
__all__ = []

import re
import threading
import unittest

from funkload.FunkLoadTestCase import FunkLoadTestCase


class Auth(FunkLoadTestCase):

    def setUp(self):
        """Setting up test."""
        self.logd("setUp")
        self.server_url = self.conf_get('main', 'url')

    _error_re = re.compile('(?s)class="error message">(.*?)</')

    def assertNoFormErrors(self, response):
        """Checks if the page returned ok and the login was sucessful."""
        self.assertEquals(response.code, 200)
        match = self._error_re.search(response.body)
        if match is not None:
            self.fail('Form contained error: %s' % match.group(1))

    def assertIsNotLoggedIn(self, response):
        # Not sure if this checking is needed.
        self.assertEquals(response.code, 200)
        match = response.body.find('If this is not you, please'
            '<a href="/+logout">log out now</a>')
        if match != -1:
            self.fail('Test failed: this user is already logged in.')

    def test_auth(self):
        """Runs the steps of a simple Launchpad login."""
        self.logd("test_auth")

        server_url = self.server_url

        # Get the login page
        response = self.get(server_url + "/+login", description="GET /+login")
        self.assertNoFormErrors(response)
        self.assertIsNotLoggedIn(response)

        # The credentials of foo user, the loginator
        email = self.conf_get('main', 'login')
        password = self.conf_get('main', 'password')

        # Get only the first form of the page, the login one,
        # and fill it
        fields = response.extractForm(path=[('form',0)], include_submit=True)
        fields['loginpage_email'] = email
        fields['loginpage_password'] = password

        # Submit the login form.
        response = self.post(
            self.absolute_url(response, '/+login'),
            fields, "POST /+login")
        self.assertNoFormErrors(response)
        self.assertIsNotLoggedIn(response)
        self.logd("logged in sucessfully")

    def absolute_url(self, response, path):
        """Calculate an absolute URL using the response and the path."""
        return '%s://%s:%s%s' % (
            response.protocol, response.server, response.port, path)

    def tearDown(self):
        """Finishes the test."""
        self.logd("tearDown.\n")


if __name__ in ('main', '__main__'):
    unittest.main()



