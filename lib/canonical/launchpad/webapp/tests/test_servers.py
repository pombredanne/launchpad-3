# Copyright Canonical Limited, 2005, all rights reserved.

__metaclass__ = type

import StringIO
import unittest

from zope.publisher.base import DefaultPublication
from zope.testing.doctest import DocTestSuite, NORMALIZE_WHITESPACE, ELLIPSIS

from canonical.launchpad.webapp.servers import (
    AnswersBrowserRequest, ApplicationServerSettingRequestFactory,
    BugsBrowserRequest, BugsPublication, LaunchpadBrowserRequest,
    TranslationsBrowserRequest, VHostWebServiceRequestPublicationFactory,
    VirtualHostRequestPublicationFactory, WebServiceRequestPublicationFactory,
    WebServiceClientRequest, WebServicePublication, WebServiceTestRequest)

from canonical.launchpad.webapp.tests import DummyConfigurationTestCase

class SetInWSGIEnvironmentTestCase(unittest.TestCase):

    def test_set(self):
        # Test that setInWSGIEnvironment() can set keys in the WSGI
        # environment.
        data = StringIO.StringIO('foo')
        env = {}
        request = LaunchpadBrowserRequest(data, env)
        request.setInWSGIEnvironment('key', 'value')
        self.assertEqual(request._orig_env['key'], 'value')

    def test_set_fails_for_existing_key(self):
        # Test that setInWSGIEnvironment() fails if the user tries to
        # set a key that existed in the WSGI environment.
        data = StringIO.StringIO('foo')
        env = {'key': 'old value'}
        request = LaunchpadBrowserRequest(data, env)
        self.assertRaises(KeyError,
                          request.setInWSGIEnvironment, 'key', 'new value')
        self.assertEqual(request._orig_env['key'], 'old value')

    def test_set_twice(self):
        # Test that setInWSGIEnvironment() can change the value of
        # keys in the WSGI environment that it had previously set.
        data = StringIO.StringIO('foo')
        env = {}
        request = LaunchpadBrowserRequest(data, env)
        request.setInWSGIEnvironment('key', 'first value')
        request.setInWSGIEnvironment('key', 'second value')
        self.assertEqual(request._orig_env['key'], 'second value')

    def test_set_after_retry(self):
        # Test that setInWSGIEnvironment() a key in the environment
        # can be set twice over a request retry.
        data = StringIO.StringIO('foo')
        env = {}
        request = LaunchpadBrowserRequest(data, env)
        request.setInWSGIEnvironment('key', 'first value')
        new_request = request.retry()
        new_request.setInWSGIEnvironment('key', 'second value')
        self.assertEqual(new_request._orig_env['key'], 'second value')


class TestApplicationServerSettingRequestFactory(unittest.TestCase):
    """Tests for the ApplicationServerSettingRequestFactory."""

    def test___call___should_set_HTTPS_env_on(self):
        # Ensure that the factory sets the HTTPS variable in the request
        # when the protocol is https.
        factory = ApplicationServerSettingRequestFactory(
            LaunchpadBrowserRequest, 'launchpad.dev', 'https', 443)
        request = factory(StringIO.StringIO(), {'HTTP_HOST': 'launchpad.dev'})
        self.assertEquals(
            request.get('HTTPS'), 'on', "factory didn't set the HTTPS env")
        # This is a sanity check ensuring that effect of this works as
        # expected with the Zope request implementation.
        self.assertEquals(request.getURL(), 'https://launchpad.dev')

    def test___call___should_not_set_HTTPS(self):
        # Ensure that the factory doesn't put an HTTPS variable in the
        # request when the protocol is http.
        factory = ApplicationServerSettingRequestFactory(
            LaunchpadBrowserRequest, 'launchpad.dev', 'http', 80)
        request = factory(StringIO.StringIO(), {})
        self.assertEquals(
            request.get('HTTPS'), None,
            "factory should not have set HTTPS env")


class TestVhostWebserviceFactory(DummyConfigurationTestCase):

    def setUp(self):
        super(TestVhostWebserviceFactory, self).setUp()
        self.factory = VHostWebServiceRequestPublicationFactory(
            'bugs', BugsBrowserRequest, BugsPublication)

    def wsgi_env(self, path, method='GET'):
        """Simulate a WSGI application environment."""
        return {
            'PATH_INFO': path,
            'HTTP_HOST': 'bugs.launchpad.dev',
            'REQUEST_METHOD': method
            }

    @property
    def working_api_path(self):
        """A path to the webservice API that should work every time."""
        return '/' + self.config.path_override

    @property
    def failing_api_path(self):
        """A path that should not work with the webservice API."""
        return '/foo'

    def test_factory_produces_webservice_objects(self):
        """The factory should produce WebService request and publication
        objects for requests to the /api root URL.
        """
        env = self.wsgi_env('/' + self.config.path_override)

        # Necessary preamble and sanity check.  We need to call
        # the factory's canHandle() method with an appropriate
        # WSGI environment before it can produce a request object for us.
        self.assert_(self.factory.canHandle(env),
            "Sanity check: The factory should be able to handle requests.")

        wrapped_factory, publication_factory = self.factory()

        # We need to unwrap the real request factory.
        request_factory = wrapped_factory.requestfactory

        self.assertEqual(request_factory, WebServiceClientRequest,
            "Requests to the /api path should return a WebService "
            "request object.")
        self.assertEqual(
            publication_factory, WebServicePublication,
            "Requests to the /api path should return a WebService "
            "publication object.")

    def test_factory_produces_normal_request_objects(self):
        """The factory should return the request and publication factories
        specified in it's constructor if the request is not bound for the
        web service.
        """
        env = self.wsgi_env('/foo')
        self.assert_(self.factory.canHandle(env),
            "Sanity check: The factory should be able to handle requests.")

        wrapped_factory, publication_factory = self.factory()

        # We need to unwrap the real request factory.
        request_factory = wrapped_factory.requestfactory

        self.assertEqual(request_factory, BugsBrowserRequest,
            "Requests to normal paths should return a Bugs "
            "request object.")
        self.assertEqual(
            publication_factory, BugsPublication,
            "Requests to normal paths should return a Bugs "
            "publication object.")

    def test_factory_processes_webservice_http_methods(self):
        """The factory should accept the HTTP methods for requests that
        should be processed by the web service.
        """
        allowed_methods = WebServiceRequestPublicationFactory.default_methods

        for method in allowed_methods:
            env = self.wsgi_env(self.working_api_path, method)
            self.assert_(self.factory.canHandle(env),
                "Sanity check")
            # Returns a tuple of (request_factory, publication_factory).
            rfactory, pfactory = self.factory.checkRequest(env)
            self.assert_(rfactory is None,
                "The '%s' HTTP method should be handled by the factory."
                % method)

    def test_factory_rejects_normal_http_methods(self):
        """The factory should reject some HTTP methods for requests that
        are *not* bound for the web service.

        This includes methods like 'PUT' and 'PATCH'.
        """
        vhost_methods = VirtualHostRequestPublicationFactory.default_methods
        ws_methods = WebServiceRequestPublicationFactory.default_methods

        denied_methods = set(ws_methods) - set(vhost_methods)

        for method in denied_methods:
            env = self.wsgi_env(self.failing_api_path, method)
            self.assert_(self.factory.canHandle(env),
                "Sanity check")
            # Returns a tuple of (request_factory, publication_factory).
            rfactory, pfactory = self.factory.checkRequest(env)
            self.assert_(rfactory is not None,
                "The '%s' HTTP method should be rejected by the factory."
                % method)

    def test_factory_understands_webservice_paths(self):
        """The factory should know if a path is directed at a web service
        resource path.
        """
        # This is a sanity check, so I can write '/api/foo' instead
        # of PATH_OVERRIDE + '/foo' in my tests.  The former's
        # intention is clearer.
        self.assertEqual(self.config.path_override, 'api',
            "Sanity check: The web service path override should be 'api'.")

        self.assert_(
            self.factory.isWebServicePath('/api'),
            "The factory should handle URLs that start with /api.")
        self.assert_(
            self.factory.isWebServicePath('/api/'),
            "The factory should handle URLs that start with /api.")

        self.assert_(
            self.factory.isWebServicePath('/api/foo'),
            "The factory should handle URLs that start with /api.")

        self.failIf(
            self.factory.isWebServicePath('/foo'),
            "The factory should not handle URLs that do not start with "
            "/api.")

        self.failIf(
            self.factory.isWebServicePath('/'),
            "The factory should not handle URLs that do not start with "
            "/api.")

        self.failIf(
            self.factory.isWebServicePath('/apifoo'),
            "The factory should not handle URLs that do not start with "
            "/api.")

        self.failIf(
            self.factory.isWebServicePath('/foo/api'),
            "The factory should not handle URLs that do not start with "
            "/api.")


class TestWebServiceRequestTraversal(DummyConfigurationTestCase):

    def test_traversal_of_api_path_urls(self):
        """Requests that have /api at the root of their path should trim
        the 'api' name from the traversal stack.
        """
        # First, we need to forge a request to the API.
        data = ''
        api_url = ('/' + self.config.path_override +
                   '/' + 'beta' + '/' + 'foo')
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
        self.assert_(self.config.path_override in stack,
            "Sanity check: the API path should show up in the request's "
            "traversal stack: %r" % stack)

        request.traverse(root)

        stack = request.getTraversalStack()
        self.failIf(self.config.path_override in stack,
            "Web service paths should be dropped from the webservice "
            "request traversal stack: %r" % stack)


class TestWebServiceRequest(unittest.TestCase):

    def test_application_url(self):
        """Requests to the /api path should return the original request's
        host, not api.launchpad.net.
        """
        # Simulate a request to bugs.launchpad.net/api
        server_url = 'http://bugs.launchpad.dev'
        env = {
            'PATH_INFO': '/api/beta',
            'SERVER_URL': server_url,
            'HTTP_HOST': 'bugs.launchpad.dev',
            }

        # WebServiceTestRequest will suffice, as it too should conform to
        # the Same Origin web browser policy.
        request = WebServiceTestRequest(environ=env)
        self.assertEqual(request.getApplicationURL(), server_url)

    def test_response_should_vary_based_on_content_type(self):
        request = WebServiceClientRequest(StringIO.StringIO(''), {})
        self.assertEquals(
            request.response.getHeader('Vary'),
            'Cookie, Authorization, Accept')


class TestBasicLaunchpadRequest(unittest.TestCase):
    """Tests for the base request class"""

    def test_baserequest_response_should_vary(self):
        """Test that our base response has a proper vary header."""
        request = LaunchpadBrowserRequest(StringIO.StringIO(''), {})
        self.assertEquals(
            request.response.getHeader('Vary'), 'Cookie, Authorization')

    def test_baserequest_response_should_vary_after_retry(self):
        """Test that our base response has a proper vary header."""
        request = LaunchpadBrowserRequest(StringIO.StringIO(''), {})
        retried_request = request.retry()
        self.assertEquals(
            retried_request.response.getHeader('Vary'),
            'Cookie, Authorization')


class TestAnswersBrowserRequest(unittest.TestCase):
    """Tests for the Answers request class."""

    def test_response_should_vary_based_on_language(self):
        request = AnswersBrowserRequest(StringIO.StringIO(''), {})
        self.assertEquals(
            request.response.getHeader('Vary'),
            'Cookie, Authorization, Accept-Language')


class TestTranslationsBrowserRequest(unittest.TestCase):
    """Tests for the Translations request class."""

    def test_response_should_vary_based_on_language(self):
        request = TranslationsBrowserRequest(StringIO.StringIO(''), {})
        self.assertEquals(
            request.response.getHeader('Vary'),
            'Cookie, Authorization, Accept-Language')


class TestLaunchpadBrowserRequest(unittest.TestCase):

    def test_query_string_params_on_get(self):
        """query_string_params is populated from the QUERY_STRING during
        GET requests."""
        request = LaunchpadBrowserRequest('', {
            'QUERY_STRING': "a=1&b=2&c=3"})
        self.assertEqual(
            request.query_string_params,
            {'a': ['1'], 'b': ['2'], 'c': ['3']},
            "The query_string_params dict is populated from the "
            "QUERY_STRING during GET requests.")

    def test_query_string_params_on_post(self):
        """query_string_params is populated from the QUERY_STRING during
        POST requests."""
        request = LaunchpadBrowserRequest('',
            {'QUERY_STRING': "a=1&b=2&c=3", 'REQUEST_METHOD': 'POST'})

        self.assertEqual(request.method, 'POST')
        self.assertEqual(
            request.query_string_params,
            {'a':['1'], 'b': ['2'], 'c': ['3']},
            "The query_string_params dict is populated from the "
            "QUERY_STRING during POST requests.")

    def test_query_string_params_empty(self):
        """The query_string_params dict is always empty when QUERY_STRING
        is empty, None or undefined.
        """
        request = LaunchpadBrowserRequest('', {'QUERY_STRING': ''})
        self.assertEqual(request.query_string_params, {})
        request = LaunchpadBrowserRequest('', {'QUERY_STRING': None})
        self.assertEqual(request.query_string_params, {})
        request = LaunchpadBrowserRequest('', {})
        self.assertEqual(request.query_string_params, {})

    def test_query_string_params_multi_value(self):
        """The query_string_params dict can include multiple values
        for a parameter."""
        request = LaunchpadBrowserRequest('', {
            'QUERY_STRING': "a=1&a=2&b=3"})
        self.assertEqual(
            request.query_string_params,
            {'a': ['1', '2'], 'b': ['3']},
            "The query_string_params dict correctly interprets multiple "
            "values for the same key in a query string.")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(
        'canonical.launchpad.webapp.servers',
        optionflags=NORMALIZE_WHITESPACE | ELLIPSIS))
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    return suite

