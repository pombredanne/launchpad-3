# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Basic ShipIt usage test."""

__metaclass__ = type
__all__ = []

import re
import threading
import unittest

from funkload.FunkLoadTestCase import FunkLoadTestCase
from funkload.Lipsum import Lipsum
import psycopg2


class ShipIt(FunkLoadTestCase):

    db_connection = None
    db_connection_lock = threading.Lock()

    def setUp(self):
        """Setting up test."""
        self.logd("setUp")

        self.server_url = self.conf_get('main', 'url')
        self.database_conninfo = self.conf_get('main', 'database_conninfo')

        self.lipsum = Lipsum()

        if ShipIt.db_connection is None:
            # We use a class variable for the database connection so the
            # same connection is shared between threads. This is important
            # for when we are running with hundreds of threads.
            ShipIt.db_connection_lock.acquire()
            try:
                if ShipIt.db_connection is None:
                    assert psycopg2.threadsafety >= 2, (
                        "psycopg2 cannot share connections between threads")
                    self.logi(
                        'Opening database connection "%s".'
                        % self.database_conninfo)
                    ShipIt.db_connection = psycopg2.connect(
                        self.database_conninfo)
                    ShipIt.db_connection.set_isolation_level(0)
            finally:
                ShipIt.db_connection_lock.release()

    def cursor(self):
        return ShipIt.db_connection.cursor()

    def get_email_validation_token(self, email):
        cur = self.cursor()
        cur.execute("""
            SELECT token FROM AuthToken
            WHERE date_consumed IS NULL AND token_type=12 AND email=%s
            """, (email,))
        row = cur.fetchone()
        if row is None:
            return None
        return row[0]

    _error_re = re.compile('(?s)class="error">.*?class="message">(.*?)</')

    def assertNoFormErrors(self, response):
        self.assertEquals(response.code, 200)
        match = self._error_re.search(response.body)
        if match is not None:
            self.fail('Form contained error "%s"' % match.group(1))

    def test_shipit(self):
        server_url = self.server_url

        self.get(server_url + "/", description="GET /")

        response = self.get(server_url + "/login", description="Get /login")
        response = response.postForm(
            0, self.post, {'submit': 'Continue'},
            'Post /+openid - OpenID authentication request')
        self.assertNoFormErrors(response)

        # User is not logged on
        email = 'user_%s@lp%s.example.com' % (
            self.lipsum.getUniqWord(), self.lipsum.getUniqWord())
        # response.postForm fails here - looks like a bug. The action
        # on the form is a relative URL and response.postForm tries
        # to retrieve it from localhost.
        params = response.extractForm(include_submit=True)
        params['field.email'] = email
        params['field.action'] = 'createaccount'
        response = self.post(
            self.absolute_url(response, '/+login-register'),
            params, "Post /+login-register - Create account")
        self.assertNoFormErrors(response)

        # Pull the email validation token from the database and
        # validate it.
        token = self.get_email_validation_token(email)
        self.assert_(token is not None, "No login token created")
        newaccount_url = self.absolute_url(
            response, '/token/%s/+newaccount' % token)
        response = self.get(
            newaccount_url, description="Get /token/[...]/+newaccount")

        # Complete the registration process.
        displayname = self.lipsum.getSubject(2)
        password = self.lipsum.getWord()
        params = response.extractForm(include_submit=True)

        params.update({
            'field.displayname': displayname,
            'field.hide_email_addresses': 'on',
            'field.password': password,
            'field.password_dupe': password,
            'field.actions.continue': 'Continue'})
        # At the moment, creating your account doesn't log you in
        # immidiately so you might end up at a 403 page - Bug #400610
        response = self.post(
            newaccount_url, params, ok_codes=[200, 302, 303, 403],
            description="Post /token/[...]/+newaccount")
        # Keep hitting the /login link until it works.
        while response.code == 403:
            login_url = self.absolute_url(response, '/login')
            response = self.get(login_url, description="Get /login")
            if response.get_base_url() == '/myrequest':
                break
            response = response.postForm(
                0, self.post, {}, "Post /+openid")
            if response.get_base_url() == '/+openid':
                params = response.extractForm()
                params['field.actions.auth'] = 'Sign In'
                response = self.post(
                    self.absolute_url(response, '/+decide'), params,
                    description = "Post /+decide",
                    ok_codes=[200, 302, 303, 403])

        # Registration succeeded - should be on the order details page now.
        self.assertEquals(response.get_base_url(), '/myrequest')

        # Request some CDs.
        params = response.extractForm(include_submit=True)
        params.update({
            'field.recipientdisplayname': displayname[:20],
            'field.addressline1': self.lipsum.getSubject(3)[:30],
            'field.addressline2': self.lipsum.getSubject(3)[:30],
            'field.city': self.lipsum.getSubject(1)[:30],
            'field.province': self.lipsum.getSubject(2)[:30],
            'field.postcode': self.lipsum.getSubject(1)[:20],
            'field.country': '212',
            'field.country-empty-marker': '1',
            'field.phone': self.lipsum.getPhoneNumber()[:16],
            'field.actions.continue': 'Submit Request'})
        response = self.post(
            self.absolute_url(response, '/myrequest'),
            params, "Post /myrequest - Request CDs")
        self.assertNoFormErrors(response)

        if response.body.find('Cancel Request') == -1:
            open('dud.html', 'w').write(response.body)

        # Confirm the request worked.
        self.assert_(
            response.body.find('Cancel Request') != -1,
            "Cancel button not found.")

        # Logout.
        response = self.post(
            server_url + "/+logout", description="Post /+logout")
        self.assert_(
            response.body.find('You have been logged out') != -1,
            "No logged out notification.")

        # Attempt to login again, bringing up the login form.
        response = self.get(server_url, description="Get /")
        response = self.get(
            server_url + "/login", description="Get /login")
        response = response.postForm(
            0, self.post, {'submit': 'Continue'},
            'Post /+openid - OpenID authentication request')
        self.assertNoFormErrors(response)

        # Submit the login form.
        params = response.extractForm(include_submit=True)
        params['field.email'] = email
        params['field.password'] = password
        params['field.action'] = 'login'
        response = self.post(
            self.absolute_url(response, '/+login-register'),
            params, "Post /+login-register - Login to existing account")
        self.assertNoFormErrors(response)
        self.assertEquals(response.url, '/myrequest')

        # Cancel the CD request.
        params = response.extractForm([('form', 1)], include_submit=True)
        response = self.post(
            self.absolute_url(response, '/myrequest'),
            params, description="Post /myrequest - Cancel CD order.")
        self.assertNoFormErrors(response)
        self.assert_(
            response.body.find('Cancel Request') == -1,
            "Cancel button found.")

        # Don't log out - leave the session dangling like most real users
        # do.

    def absolute_url(self, response, path):
        """Calculate an absolute URL using the response and the path."""
        return '%s://%s:%s%s' % (
            response.protocol, response.server, response.port, path)

    def tearDown(self):
        """Setting up test."""
        self.logd("tearDown.\n")



if __name__ in ('main', '__main__'):
    unittest.main()
