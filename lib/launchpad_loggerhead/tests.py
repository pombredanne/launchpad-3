# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import lazr.uri
from paste.httpexceptions import HTTPExceptionHandler
import requests
from six.moves.urllib_parse import (
    urlencode,
    urlsplit,
    )
import soupmatchers
from testtools.content import Content
from testtools.content_type import UTF8_TEXT
import wsgi_intercept
from wsgi_intercept.urllib2_intercept import (
    install_opener,
    uninstall_opener,
    )
import wsgi_intercept.zope_testbrowser
from zope.security.proxy import removeSecurityProxy

from launchpad_loggerhead.app import RootApp
from launchpad_loggerhead.session import SessionHandler
from launchpad_loggerhead.testing import LoggerheadFixture
from lp.app.enums import InformationType
from lp.services.config import config
from lp.services.webapp.vhosts import allvhosts
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    AppServerLayer,
    DatabaseFunctionalLayer,
    )


SESSION_VAR = 'lh.session'

# See lib/launchpad_loggerhead/wsgi.py for the production mechanism for
# getting the secret.
SECRET = 'secret'


def session_scribbler(app, test):
    """Squirrel away the session variable."""
    def scribble(environ, start_response):
        test.session = environ[SESSION_VAR]  # Yay for mutables.
        return app(environ, start_response)
    return scribble


def dummy_destination(environ, start_response):
    """Return a fake response."""
    start_response('200 OK', [('Content-type', 'text/plain')])
    return ['This is a dummy destination.\n']


class SimpleLogInRootApp(RootApp):
    """A mock root app that doesn't require open id."""
    def _complete_login(self, environ, start_response):
        environ[SESSION_VAR]['user'] = 'bob'
        start_response('200 OK', [('Content-type', 'text/plain')])
        return ['\n']


class TestLogout(TestCase):
    layer = DatabaseFunctionalLayer

    def intercept(self, uri, app):
        """Install wsgi interceptors for the uri, app tuple."""
        if isinstance(uri, basestring):
            uri = lazr.uri.URI(uri)
        port = uri.port
        if port is None:
            if uri.scheme == 'http':
                port = 80
            elif uri.scheme == 'https':
                port = 443
            else:
                raise NotImplementedError(uri.scheme)
        else:
            port = int(port)
        wsgi_intercept.add_wsgi_intercept(uri.host, port, lambda: app)
        self.intercepted.append((uri.host, port))

    def setUp(self):
        TestCase.setUp(self)
        self.intercepted = []
        self.session = None
        self.root = app = SimpleLogInRootApp(SESSION_VAR)
        app = session_scribbler(app, self)
        app = HTTPExceptionHandler(app)
        app = SessionHandler(app, SESSION_VAR, SECRET)
        self.cookie_name = app.cookie_handler.cookie_name
        self.intercept(config.codehosting.secure_codebrowse_root, app)
        self.intercept(allvhosts.configs['mainsite'].rooturl,
                       dummy_destination)
        install_opener()
        self.browser = wsgi_intercept.zope_testbrowser.WSGI_Browser()
        # We want to pretend we are not a robot, or else mechanize will honor
        # robots.txt.
        self.browser.mech_browser.set_handle_robots(False)
        self.browser.open(
            config.codehosting.secure_codebrowse_root + '+login')

    def tearDown(self):
        uninstall_opener()
        for host, port in self.intercepted:
            wsgi_intercept.remove_wsgi_intercept(host, port)
        TestCase.tearDown(self)

    def testLoggerheadLogout(self):
        # We start logged in as 'bob'.
        self.assertEqual(self.session['user'], 'bob')
        self.browser.open(
            config.codehosting.secure_codebrowse_root + 'favicon.ico')
        self.assertEqual(self.session['user'], 'bob')
        self.assertTrue(self.browser.cookies.get(self.cookie_name))

        # When we visit +logout, our session is gone.
        self.browser.open(
            config.codehosting.secure_codebrowse_root + '+logout')
        self.assertEqual(self.session, {})

        # By default, we have been redirected to the Launchpad root.
        self.assertEqual(
            self.browser.url, allvhosts.configs['mainsite'].rooturl)

        # The session cookie still exists, because of how
        # paste.auth.cookie works (see
        # http://trac.pythonpaste.org/pythonpaste/ticket/139 ) but the user
        # does in fact have an empty session now.
        self.browser.open(
            config.codehosting.secure_codebrowse_root + 'favicon.ico')
        self.assertEqual(self.session, {})

    def testLoggerheadLogoutRedirect(self):
        # When we visit +logout with a 'next_to' value in the query string,
        # the logout page will redirect to the given URI.  As of this
        # writing, this is used by Launchpad to redirect to our OpenId
        # provider (see lp.testing.tests.test_login.
        # TestLoginAndLogout.test_CookieLogoutPage).

        # Here, we will have a more useless example of the basic machinery.
        dummy_root = 'http://dummy.dev/'
        self.intercept(dummy_root, dummy_destination)
        self.browser.open(
            config.codehosting.secure_codebrowse_root +
            '+logout?' + urlencode(dict(next_to=dummy_root + '+logout')))

        # We are logged out, as before.
        self.assertEqual(self.session, {})

        # Now, though, we are redirected to the ``next_to`` destination.
        self.assertEqual(self.browser.url, dummy_root + '+logout')
        self.assertEqual(self.browser.contents,
                         'This is a dummy destination.\n')


class TestWSGI(TestCaseWithFactory):
    """Smoke tests for Launchpad's loggerhead WSGI server."""

    layer = AppServerLayer

    def setUp(self):
        super(TestWSGI, self).setUp()
        self.useBzrBranches()
        loggerhead_fixture = self.useFixture(LoggerheadFixture())

        def get_debug_log_bytes():
            try:
                with open(loggerhead_fixture.logfile, "rb") as logfile:
                    return [logfile.read()]
            except IOError:
                return [b""]

        self.addDetail(
            "loggerhead-debug", Content(UTF8_TEXT, get_debug_log_bytes))

    def test_public_port_public_branch(self):
        # Requests for public branches on the public port are allowed.
        db_branch, _ = self.create_branch_and_tree()
        branch_url = "http://127.0.0.1:%d/%s" % (
            config.codebrowse.port, db_branch.unique_name)
        response = requests.get(branch_url)
        self.assertEqual(200, response.status_code)
        title_tag = soupmatchers.Tag(
            "page title", "title", text="%s : changes" % db_branch.unique_name)
        self.assertThat(response.text, soupmatchers.HTMLContains(title_tag))

    def test_public_port_private_branch(self):
        # Requests for private branches on the public port send the user
        # through the login workflow.
        db_branch, _ = self.create_branch_and_tree(
            information_type=InformationType.USERDATA)
        naked_branch = removeSecurityProxy(db_branch)
        branch_url = "http://127.0.0.1:%d/%s" % (
            config.codebrowse.port, naked_branch.unique_name)
        response = requests.get(
            branch_url, headers={"X-Forwarded-Scheme": "https"},
            allow_redirects=False)
        self.assertEqual(301, response.status_code)
        self.assertEqual(
            "testopenid.dev:8085",
            urlsplit(response.headers["Location"]).netloc)

    def test_private_port_public_branch(self):
        # Requests for public branches on the private port are allowed.
        db_branch, _ = self.create_branch_and_tree()
        branch_url = "http://127.0.0.1:%d/%s" % (
            config.codebrowse.private_port, db_branch.unique_name)
        response = requests.get(branch_url)
        self.assertEqual(200, response.status_code)
        title_tag = soupmatchers.Tag(
            "page title", "title", text="%s : changes" % db_branch.unique_name)
        self.assertThat(response.text, soupmatchers.HTMLContains(title_tag))

    def test_private_port_private_branch(self):
        # Requests for private branches on the private port are allowed.
        db_branch, _ = self.create_branch_and_tree(
            information_type=InformationType.USERDATA)
        naked_branch = removeSecurityProxy(db_branch)
        branch_url = "http://127.0.0.1:%d/%s" % (
            config.codebrowse.private_port, naked_branch.unique_name)
        response = requests.get(branch_url)
        self.assertEqual(200, response.status_code)
        title_tag = soupmatchers.Tag(
            "page title", "title",
            text="%s : changes" % naked_branch.unique_name)
        self.assertThat(response.text, soupmatchers.HTMLContains(title_tag))
