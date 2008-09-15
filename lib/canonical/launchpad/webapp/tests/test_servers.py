# Copyright Canonical Limited, 2005, all rights reserved.

__metaclass__ = type

import StringIO
import unittest

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
            API_PATH_OVERRIDE)

        factory = WebServiceRequestPublicationFactory(
            'api', WebServiceClientRequest, WebServicePublication)

        def path_info(path):
            # Simulate a WSGI environment.
            return {'PATH_INFO': path}

        # This is a sanity check, so I can write '/api/foo' instead
        # of API_ROOT_PATH + '/foo' -- the former's intention is clearer.
        self.assert(API_PATH_OVERRIDE == 'api')

        self.assert(factory.canHandle(path_info('/api'))
        self.assert(factory.canHandle(path_info('/api/foo'))
        self.failIf(factory.canHandle(path_info('/foo'))
        self.failIf(factory.canHandle(path_info('/apifoo'))
        self.failIf(factory.canHandle(path_info('/foo/api'))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(
        'canonical.launchpad.webapp.servers',
        optionflags=NORMALIZE_WHITESPACE | ELLIPSIS))
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    return suite

