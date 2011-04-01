# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import cStringIO
import errno
import logging
import unittest
import urllib
import socket
import re

import lazr.uri
import wsgi_intercept
from wsgi_intercept.urllib2_intercept import install_opener, uninstall_opener
import wsgi_intercept.zope_testbrowser
from paste import httpserver
from paste.httpexceptions import HTTPExceptionHandler
import zope.event

from canonical.config import config
from canonical.launchpad.webapp.errorlog import ErrorReport, ErrorReportEvent
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.testing.layers import DatabaseFunctionalLayer
from launchpad_loggerhead.app import (
    _oops_html_template,
    oops_middleware,
    RootApp,
    )
from launchpad_loggerhead.session import SessionHandler
from lp.testing import TestCase

SESSION_VAR = 'lh.session'

# See sourcecode/launchpad-loggerhead/start-loggerhead.py for the production
# mechanism for getting the secret.
SECRET = 'secret'


def session_scribbler(app, test):
    """Squirrel away the session variable."""
    def scribble(environ, start_response):
        test.session = environ[SESSION_VAR] # Yay for mutables.
        return app(environ, start_response)
    return scribble


def dummy_destination(environ, start_response):
    """Return a fake response."""
    start_response('200 OK', [('Content-type','text/plain')])
    return ['This is a dummy destination.\n']


class SimpleLogInRootApp(RootApp):
    """A mock root app that doesn't require open id."""
    def _complete_login(self, environ, start_response):
        environ[SESSION_VAR]['user'] = 'bob'
        start_response('200 OK', [('Content-type','text/plain')])
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
        self.intercept(config.codehosting.codebrowse_root, app)
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
        self.failUnless(self.browser.cookies.get(self.cookie_name))

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
        # provider (see canonical.launchpad.tests.test_login.
        # TestLoginAndLogout.test_CookieLogoutPage).

        # Here, we will have a more useless example of the basic machinery.
        dummy_root = 'http://dummy.dev/'
        self.intercept(dummy_root, dummy_destination)
        self.browser.open(
            config.codehosting.secure_codebrowse_root +
            '+logout?' +
            urllib.urlencode(dict(next_to=dummy_root + '+logout')))

        # We are logged out, as before.
        self.assertEqual(self.session, {})

        # Now, though, we are redirected to the ``next_to`` destination.
        self.assertEqual(self.browser.url, dummy_root + '+logout')
        self.assertEqual(self.browser.contents,
                         'This is a dummy destination.\n')


class TestOopsMiddleware(TestCase):

    def setUp(self):
        super(TestOopsMiddleware, self).setUp()
        self.start_response_called = False

    def assertContainsRe(self, haystack, needle_re, flags=0):
        """Assert that a contains something matching a regular expression."""
        # There is: self.assertTextMatchesExpressionIgnoreWhitespace
        #           but it does weird things with whitespace, and gives
        #           unhelpful error messages when it fails, so this is copied
        #           from bzrlib
        if not re.search(needle_re, haystack, flags):
            if '\n' in haystack or len(haystack) > 60:
                # a long string, format it in a more readable way
                raise AssertionError(
                        'pattern "%s" not found in\n"""\\\n%s"""\n'
                        % (needle_re, haystack))
            else:
                raise AssertionError('pattern "%s" not found in "%s"'
                        % (needle_re, haystack))

    def catchLogEvents(self):
        """Any log events that are triggered get written to self.log_stream"""
        logger = logging.getLogger('lp-loggerhead')
        logger.setLevel(logging.DEBUG)
        self.log_stream = cStringIO.StringIO()
        handler = logging.StreamHandler(self.log_stream)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)

    def runtime_failing_app(self, environ, start_response):
        if False:
            yield None
        raise RuntimeError('just a generic runtime error.')

    def socket_failing_app(self, environ, start_response):
        if False:
            yield None
        raise socket.error(errno.EPIPE, 'Connection closed')

    def logging_start_response(self, status, response_headers, exc_info=None):
        self._response_chunks = []
        def _write(chunk):
            self._response_chunks.append(chunk)
        self.start_response_called = True
        return _write

    def success_app(self, environ, start_response):
        writer = start_response('200 OK', {})
        writer('Successfull\n')
        return []

    def failing_start_response(self, status, response_headers, exc_info=None):
        def fail_write(chunk):
            raise socket.error(errno.EPIPE, 'Connection closed')
        self.start_response_called = True
        return fail_write

    def multi_yielding_app(self, environ, start_response):
        writer = start_response('200 OK', {})
        yield 'content\n'
        yield 'I want\n'
        yield 'to give to the user\n'

    def no_body_app(self, environ, start_response):
        writer = start_response('200 OK', {})
        return []

    def _get_default_environ(self):
        return {'wsgi.version': (1, 0),
                'wsgi.url_scheme': 'http',
                'PATH_INFO': '/test/path',
                'REQUEST_METHOD': 'GET',
                'SERVER_NAME': 'localhost',
                'SERVER_PORT': '8080',
               }

    def wrap_and_run(self, app, failing_write=False):
        app = oops_middleware(app)
        # Just random env data, rather than setting up a whole wsgi stack just
        # to pass in values for this dict
        environ = self._get_default_environ()
        if failing_write:
            result = list(app(environ, self.failing_start_response))
        else:
            result = list(app(environ, self.logging_start_response))
        return result

    def test_exception_triggers_oops(self):
        res = self.wrap_and_run(self.runtime_failing_app)
        # After the exception was raised, we should also have gotten an oops
        # event
        self.assertEqual(1, len(self.oopses))
        oops = self.oopses[0]
        self.assertEqual('RuntimeError', oops.type)
        # runtime_failing_app doesn't call start_response, but oops_middleware
        # does because it tries to send the OOPS information to the user.
        self.assertTrue(self.start_response_called)
        self.assertEqual(_oops_html_template % {'oopsid': oops.id},
                         ''.join(self._response_chunks))

    def test_ignores_socket_exceptions(self):
        self.catchLogEvents()
        res = self.wrap_and_run(self.socket_failing_app)
        self.assertEqual(0, len(self.oopses))
        self.assertContainsRe(self.log_stream.getvalue(),
            'Caught socket exception from <unknown>:.*Connection closed')
        # start_response doesn't get called because the app fails first,
        # and oops_middleware knows not to do anything with a closed socket.
        self.assertFalse(self.start_response_called)

    def test_ignores_writer_failures(self):
        self.catchLogEvents()
        res = self.wrap_and_run(self.success_app, failing_write=True)
        self.assertEqual(0, len(self.oopses))
        self.assertContainsRe(self.log_stream.getvalue(),
            'Caught socket exception from <unknown>:.*Connection closed')
        # success_app calls start_response, so this should get passed on.
        self.assertTrue(self.start_response_called)

    def test_stopping_early_no_oops(self):
        # See bug #726985.
        # If content is being streamed, and the pipe closes, we'll get a
        # 'GeneratorExit', because it is closed before finishing. This doesn't
        # need to become an OOPS.
        self.catchLogEvents()
        app = oops_middleware(self.multi_yielding_app)
        environ = self._get_default_environ()
        result = app(environ, self.logging_start_response)
        self.assertEqual('content\n', result.next())
        # At this point, we intentionally kill the app and the response, so
        # that they will get GeneratorExit
        del app, result
        self.assertEqual([], self.oopses)
        self.assertContainsRe(self.log_stream.getvalue(),
            'Caught GeneratorExit from <unknown>')
        # Body content was yielded, we must have called start_response
        self.assertTrue(self.start_response_called)

    def test_no_body_calls_start_response(self):
        # See bug #732481, even if we don't have a body, if we have headers to
        # send, we must call start_response
        result = self.wrap_and_run(self.no_body_app)
        self.assertEqual([], result)
        self.assertTrue(self.start_response_called)
        # Output content is empty because of no_body_app
        self.assertEqual('', ''.join(self._response_chunks))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
