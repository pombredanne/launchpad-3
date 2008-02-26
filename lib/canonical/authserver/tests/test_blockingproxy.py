# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the in-memory `ServerProxy` objects."""

__metaclass__ = type

import re
import xmlrpclib

from bzrlib.transport import Server
from bzrlib.tests import iter_suite_tests, TestLoader, TestScenarioApplier

from canonical.authserver.client import InMemoryBlockingProxy
from canonical.authserver.xmlrpc import defer_to_thread
from canonical.testing import TwistedLayer

from twisted.application import strports
from twisted.web import server, resource, xmlrpc
from twisted.trial import unittest


class MockXMLRPCObject:
    """XML-RPC object that logs all of its calls."""

    def __init__(self):
        self.log = []

    def _getMethods(self):
        """Return a list of method names to be published over XML-RPC.

        This is a convenience for us to keep the names of the published
        methods close to the methods themselves. It isn't part of the
        interface for anything except our test servers.
        """
        return ['returnsNone', 'returnsValue', 'success', 'takesArguments']

    def returnsNone(self):
        """This method returns None.

        Used to check that our proxies correctly handle methods that return
        types of objects that are unsupported by XML-RPC.
        """
        return None

    def returnsValue(self, value):
        """Used to check that the proxy passes on the return value."""
        return value

    def success(self):
        """Used to check that the proxy actually calls underlying methods."""
        self.log.append('success')
        return ''

    def takesArguments(self, *args):
        """Used to check the proxy passes in arguments from the client."""
        self.log.append(('takesArguments', args))
        return ''

    def unpublished(self):
        """This method should never be called over XML-RPC."""
        self.log.append('unpublished')


class TestBlockingProxyConformance(unittest.TestCase):
    """Interface conformance tests for blocking XML-RPC proxies.

    These tests check that our in-memory proxy behaves like a real xmlrpclib
    `ServerProxy`. They are parametrized using bzrlib's `TestScenarioApplier`.

    The `server_factory` instance variable is set by the test loader to one of
    `TwistedServer` or `InMemoryServer`. It's expected that `server_factory`
    takes a single `XMLRPC` object as an argument and returns an object that
    has `setUp`, `tearDown` and `getBlockingProxy` methods, with the latter
    returning a proxy that conforms to these tests.

    The tests are closely bound to `MockXMLRPCObject`.
    """

    layer = TwistedLayer

    def setUp(self):
        self.xmlrpc_resource = MockXMLRPCObject()
        self.server = self.server_factory(self.xmlrpc_resource)
        self.server.setUp()

    def tearDown(self):
        self.server.tearDown()

    def makeProxy(self):
        """Return an instance of the proxy to test."""
        return self.server.getBlockingProxy()

    def assertContainsRe(self, haystack, needle_re):
        """Assert that a contains something matching a regular expression."""
        if not re.search(needle_re, haystack):
            if '\n' in haystack or len(haystack) > 60:
                # a long string, format it in a more readable way
                raise AssertionError(
                        'pattern "%s" not found in\n"""\\\n%s"""\n'
                        % (needle_re, haystack))
            else:
                raise AssertionError('pattern "%s" not found in "%s"'
                        % (needle_re, haystack))

    def assertRaisesFault(self, code, regex, function, *arguments):
        """Assert that `function` raises a particular Fault.

        Asserts that the Fault's code and string match what we expect.
        """
        exception = self.assertRaises(xmlrpclib.Fault, function, *arguments)
        self.assertEqual(code, exception.faultCode)
        self.assertContainsRe(exception.faultString, regex)

    def assertLogMatches(self, expected):
        """Assert that the log on `xmlrpc_resource` matches `expected`."""
        self.assertEqual(expected, self.xmlrpc_resource.log)

    @defer_to_thread
    def test_callsUnderlyingImplementation(self):
        # callRemote('method_name') calls that method on the server.
        proxy = self.makeProxy()
        proxy.success()
        self.assertLogMatches(['success'])

    @defer_to_thread
    def test_passesArguments(self):
        # Extra argument passed to a proxied method are passed on to the
        # remote method on the server.
        proxy = self.makeProxy()
        proxy.takesArguments(2, 3, 5)
        self.assertLogMatches([('takesArguments', (2, 3, 5))])

    @defer_to_thread
    def test_returnsValue(self):
        # The value returned from the remote method is returned by the proxied
        # method.
        proxy = self.makeProxy()
        result = proxy.returnsValue(42)
        self.assertEqual(result, 42)

    @defer_to_thread
    def test_methodDoesntExist(self):
        # The proxy raises a Fault when we try to call a method that doesn't
        # exist on the remote object.
        proxy = self.makeProxy()
        self.assertRaisesFault(
            8001, 'function doesntExist not found', proxy.doesntExist, 42)

    @defer_to_thread
    def test_unpublished(self):
        # An 'unpublished' method is a method on the remote object that is not
        # intended to be called remotely. For Twisted XML-RPC resources, this
        # is a method not prefixed by 'xmlrpc_'. When we call an unpublished
        # method, the proxy behaves as if it doesn't exist.
        proxy = self.makeProxy()
        self.assertRaisesFault(
            8001, 'function unpublished not found', proxy.unpublished)

    @defer_to_thread
    def test_unsupportedTypeForParameter(self):
        # Only certain types can go over the wire. If we pass in bad arguments
        # to the proxy, it raises a TypeError.
        proxy = self.makeProxy()
        self.assertRaises(TypeError, proxy.takesArguments, None)

    @defer_to_thread
    def test_returnsUnsupportedType(self):
        # If the remote method returns something that can't go over the wire,
        # the proxy raises a Fault.
        proxy = self.makeProxy()
        self.assertRaisesFault(
            8002, "can't serialize output", proxy.returnsNone)


class TwistedServer(Server):
    """A test HTTP server that serves an XML-RPC resource.

    Use `getBlockingProxy` to get a real proxy (i.e. an
    `xmlrpclib.ServerProxy`) that points to the resource.
    """

    def __init__(self, xmlrpc_object):
        self.xmlrpc_resource = self._makeResource(xmlrpc_object)
        self._service = None

    def _makeResource(self, xmlrpc_object):
        method_names = xmlrpc_object._getMethods()
        xmlrpc_resource = xmlrpc.XMLRPC()
        for method_name in method_names:
            method = getattr(xmlrpc_object, method_name)
            setattr(xmlrpc_resource, 'xmlrpc_%s' % method_name, method)
        return xmlrpc_resource

    def setUp(self):
        root = resource.Resource()
        root.putChild('xmlrpc', self.xmlrpc_resource)
        site = server.Site(root)
        self._service = strports.service('tcp:0', site)
        self._service.startService()

    def get_url(self):
        return 'http://localhost:%s/xmlrpc' % (
            self._service._port.getHost().port)

    def tearDown(self):
        self._service.stopService()

    def getBlockingProxy(self):
        return xmlrpclib.ServerProxy(self.get_url())


class InMemoryServer(Server):
    """A test HTTP server that serves an XML-RPC resource."""

    def __init__(self, xmlrpc_object):
        self.xmlrpc_object = xmlrpc_object

    def setUp(self):
        pass

    def get_url(self):
        return None

    def tearDown(self):
        pass

    def getBlockingProxy(self):
        return InMemoryBlockingProxy(
            self.xmlrpc_object, self.xmlrpc_object._getMethods())


def load_tests(tests, module, loader):
    applier = TestScenarioApplier()
    applier.scenarios = [
        ('memory', {'server_factory': InMemoryServer}),
        ('http', {'server_factory': TwistedServer})]
    result = loader.suiteClass()
    for test in iter_suite_tests(tests):
        result.addTests(applier.adapt(test))
    return result


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
