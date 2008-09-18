# Copyright Canonical Limited, 2005, all rights reserved.

__metaclass__ = type

import StringIO
import unittest
import urlparse

from zope.testing.doctest import DocTestSuite, NORMALIZE_WHITESPACE, ELLIPSIS


class SetInWSGIEnvironmentTestCase(unittest.TestCase):

    def test_set(self):
        # Test that setInWSGIEnvironment() can set keys in the WSGI
        # environment.
        from canonical.launchpad.webapp.servers import LaunchpadBrowserRequest
        data = StringIO.StringIO('foo')
        env = {}
        request = LaunchpadBrowserRequest(data, env)
        request.setInWSGIEnvironment('key', 'value')
        self.assertEqual(request._orig_env['key'], 'value')

    def test_set_fails_for_existing_key(self):
        # Test that setInWSGIEnvironment() fails if the user tries to
        # set a key that existed in the WSGI environment.
        from canonical.launchpad.webapp.servers import LaunchpadBrowserRequest
        data = StringIO.StringIO('foo')
        env = {'key': 'old value'}
        request = LaunchpadBrowserRequest(data, env)
        self.assertRaises(KeyError,
                          request.setInWSGIEnvironment, 'key', 'new value')
        self.assertEqual(request._orig_env['key'], 'old value')

    def test_set_twice(self):
        # Test that setInWSGIEnvironment() can change the value of
        # keys in the WSGI environment that it had previously set.
        from canonical.launchpad.webapp.servers import LaunchpadBrowserRequest
        data = StringIO.StringIO('foo')
        env = {}
        request = LaunchpadBrowserRequest(data, env)
        request.setInWSGIEnvironment('key', 'first value')
        request.setInWSGIEnvironment('key', 'second value')
        self.assertEqual(request._orig_env['key'], 'second value')

    def test_set_after_retry(self):
        # Test that setInWSGIEnvironment() a key in the environment
        # can be set twice over a request retry.
        from canonical.launchpad.webapp.servers import LaunchpadBrowserRequest
        data = StringIO.StringIO('foo')
        env = {}
        request = LaunchpadBrowserRequest(data, env)
        request.setInWSGIEnvironment('key', 'first value')
        new_request = request.retry()
        new_request.setInWSGIEnvironment('key', 'second value')
        self.assertEqual(new_request._orig_env['key'], 'second value')


class TestWebServiceRequestPublicationFactory(unittest.TestCase):

    def test_factory_only_handles_urls_with_api_path(self):
        """Requests with URLs containing the webservice API root should
        be handled by the factory.  URLs without the path should not
        be handled.
        """
        from canonical.launchpad.webapp.servers import (
            WebServiceRequestPublicationFactory,
            WebServiceClientRequest,
            WebServicePublication,
            WEBSERVICE_PATH_OVERRIDE)

        factory = WebServiceRequestPublicationFactory(
            'api', WebServiceClientRequest, WebServicePublication)

        def path_info(path):
            # Simulate a WSGI environment.
            return {'PATH_INFO': path}

        # This is a sanity check, so I can write '/api/foo' instead
        # of WEBSERVICE_PATH_OVERRIDE + '/foo' in my tests.  The former's
        # intention is clearer.
        self.assert_(WEBSERVICE_PATH_OVERRIDE == 'api')

        self.assert_(factory.canHandle(path_info('/api')),
            "The factory should handle URLs that start with /api.")

        self.assert_(factory.canHandle(path_info('/api/foo')),
            "The factory should handle URLs that start with /api.")

        self.failIf(factory.canHandle(path_info('/foo')),
            "The factory should not handle URLs that do not start with "
            "/api, and that are not addressed to the webservice domain.")

        self.failIf(factory.canHandle(path_info('/')),
            "The factory should not handle URLs that do not start with "
            "/api, and that are not addressed to the webservice domain.")

        self.failIf(factory.canHandle(path_info('/apifoo')),
            "The factory should not handle URLs that do not start with "
            "/api, and that are not addressed to the webservice domain.")

        self.failIf(factory.canHandle(path_info('/foo/api')),
            "The factory should not handle URLs that do not start with "
            "/api, and that are not addressed to the webservice domain.")


class TestWebServiceRequestTraversal(unittest.TestCase):

    def test_traversal_of_api_path_urls(self):
        """Requests that have /api at the root of their path should trim
        the 'api' name from the traversal stack.
        """
        from canonical.launchpad.webapp.servers import (
            WebServiceClientRequest,
            WEBSERVICE_PATH_OVERRIDE)
        from zope.publisher.base import DefaultPublication

        # First, we need to forge a request to the API.
        data = ''
        api_url = '/' + WEBSERVICE_PATH_OVERRIDE + '/' + 'beta' + '/' + 'foo'
        env = {'PATH_INFO': api_url}
        request = WebServiceClientRequest(data, env)

        # And we need a mock publication object to use during traversal.
        class WebServicePublicationStub(DefaultPublication):
            def getResource(self, request, obj):
                pass

        request.setPublication(WebServicePublicationStub(None))

        # And we need a traversible object that knows about the 'foo' name.
        root = {'foo': object()}

        stack = request.getTraversalStack()
        self.assert_(WEBSERVICE_PATH_OVERRIDE in stack,
            "Sanity check: the API path should show up in the request's "
            "traversal stack: %r" % stack)

        request.traverse(root)

        stack = request.getTraversalStack()
        self.failIf(WEBSERVICE_PATH_OVERRIDE in stack,
            "Web service paths should be dropped from the webservice "
            "request traversal stack: %r" % stack)


class TestWebServiceRequest(unittest.TestCase):

    def test_application_url(self):
        """Requests to the /api path should return the original request's
        host, not api.launchpad.net.
        """
        # WebServiceTestRequest will suffice, as it too should conform to
        # the Same Origin web browser policy.
        from canonical.launchpad.webapp.servers import WebServiceTestRequest

        # Simulate a request to bugs.launchpad.net/api
        server_url = 'http://bugs.launchpad.dev'
        env = {
            'PATH_INFO': '/api/beta',
            'SERVER_URL': server_url,
            'HTTP_HOST': 'bugs.launchpad.dev',
            }

        request = WebServiceTestRequest(environ=env)
        self.assertEqual(request.getApplicationURL(), server_url)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(
        'canonical.launchpad.webapp.servers',
        optionflags=NORMALIZE_WHITESPACE | ELLIPSIS))
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    return suite

