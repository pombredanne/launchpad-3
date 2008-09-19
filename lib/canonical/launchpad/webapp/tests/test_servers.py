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


class TestVhostWebserviceFactory(unittest.TestCase):

    def test_factory_produces_webservice_objects(self):
        """The factory should produce WebService request and publication
        objects for requests to the /api root URL.
        """
        from canonical.launchpad.webapp.servers import (
            VHostWebServiceRequestPublicationFactory,
            BugsBrowserRequest,
            BugsPublication,
            WebServiceClientRequest,
            WebServicePublication,
            WEBSERVICE_PATH_OVERRIDE)

        def path_info(path):
            # Simulate a WSGI environment.
            return {'PATH_INFO': path}

        factory = VHostWebServiceRequestPublicationFactory(
            'bugs', BugsBrowserRequest, BugsPublication)

        env = path_info(WEBSERVICE_PATH_OVERRIDE)

        # Necessary preamble and sanity check.  We need to call
        # the factory's canHandle() method with an appropriate
        # WSGI environment before it can produce a request object for us.
        self.assert_(factory.canHandle(env),
            "Sanity check: The factory should be able to handle requests.")

        request = factory()

        self.assertEqual(request.__class__, WebServiceClientRequest,
            "Requests to the /api path should return a WebService "
            "request object.")
        self.assertEqual(
            request.publication.__class__, WebServicePublication,
            "Requests to the /api path should return a WebService "
            "publication object.")

        env = path_info('/foo')
        self.assert_(factory.canHandle(env),
            "Sanity check: The factory should be able to handle requests.")

        request = factory()

        self.assertEqual(request.__class__, BugsBrowserRequest,
            "Requests to normal paths should return a Bugs "
            "request object.")
        self.assertEqual(
            request.publication.__class__, BugsPublication,
            "Requests to normal paths should return a Bugs "
            "publication object.")

    def test_factory_understands_webservice_paths(self):
        """The factory should know if a path is directed at a web service
        resource path.
        """
        from canonical.launchpad.webapp.servers import (
            VHostWebServiceRequestPublicationFactory,
            BugsBrowserRequest,
            BugsPublication,
            WEBSERVICE_PATH_OVERRIDE)

        # This is a sanity check, so I can write '/api/foo' instead
        # of WEBSERVICE_PATH_OVERRIDE + '/foo' in my tests.  The former's
        # intention is clearer.
        self.assert_(WEBSERVICE_PATH_OVERRIDE == 'api')

        factory = VHostWebServiceRequestPublicationFactory(
            'bugs', BugsBrowserRequest, BugsPublication)

        self.assert_(
            factory.isWebServicePath('/api'),
            "The factory should handle URLs that start with /api.")
        self.assert_(
            factory.isWebServicePath('/api/'),
            "The factory should handle URLs that start with /api.")

        self.assert_(
            factory.isWebServicePath('/api/foo'),
            "The factory should handle URLs that start with /api.")

        self.failIf(
            factory.isWebServicePath('/foo'),
            "The factory should not handle URLs that do not start with "
            "/api.")

        self.failIf(
            factory.isWebServicePath('/'),
            "The factory should not handle URLs that do not start with "
            "/api.")

        self.failIf(
            factory.isWebServicePath('/apifoo'),
            "The factory should not handle URLs that do not start with "
            "/api.")

        self.failIf(
            factory.isWebServicePath('/foo/api'),
            "The factory should not handle URLs that do not start with "
            "/api.")


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

