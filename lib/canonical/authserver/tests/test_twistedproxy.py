# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the in-memory `ServerProxy` objects."""

__metaclass__ = type

import re

from bzrlib.transport import Server
from bzrlib.tests import iter_suite_tests, TestLoader, TestScenarioApplier

from canonical.authserver.client import InMemoryTwistedProxy
from canonical.testing import TwistedLayer

from twisted.application import strports
from twisted.web import server, resource, xmlrpc
from twisted.trial import unittest


class MockXMLRPCObject(xmlrpc.XMLRPC):
    """XML-RPC object that logs all of its calls."""

    def __init__(self):
        xmlrpc.XMLRPC.__init__(self)
        self.log = []

    def xmlrpc_returnsNone(self):
        """This method returns None.

        Used to check that our proxies correctly handle methods that return
        types of objects that are not unsupported by XML-RPC.
        """
        return None

    def xmlrpc_returnsValue(self, value):
        """Used to check that the proxy passes on the return value."""
        return value

    def xmlrpc_success(self):
        """Used to check that the proxy actually calls underlying methods."""
        self.log.append('success')
        return ''

    def xmlrpc_takesArguments(self, *args):
        """Used to check the proxy passes in arguments from the client."""
        self.log.append(('takesArguments', args))
        return ''

    def unpublished(self):
        """This method should never be called over XML-RPC."""
        self.log.append('unpublished')


class TestTwistedProxyConformance(unittest.TestCase):
    """Interface conformance tests for Twisted XML-RPC proxies.

    These tests check that our in-memory proxy behaves like a real Twisted
    XML-RPC proxy. They are parametrized using bzrlib's `TestScenarioApplier`.

    The `server_factory` instance variable is set by the test loader to one of
    `TwistedServer` or `InMemoryServer`. It's expected that `server_factory`
    takes a single `XMLRPC` object as an argument and returns an object that
    has `setUp`, `tearDown` and `getTwistedProxy` methods, with the latter
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
        return self.server.getTwistedProxy()

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

    def assertFault(self, deferred, code, regex):
        """Assert that `deferred` will errback with a an XML-RPC Fault.

        The fault is expected to have the given `code` and have a message that
        `regex` matches (in Python terms, 'searches').
        """
        deferred = self.assertFailure(deferred, xmlrpc.Fault)
        def check_fault(fault):
            self.assertEqual(code, fault.faultCode)
            self.assertContainsRe(fault.faultString, regex)
            return fault
        return deferred.addCallback(check_fault)

    def checkLog(self, ignored, expected):
        """Callback that checks the log on `self.xmlrpc_resource`.

        Asserts that the log on `self.xmlrpc_resource` is equal to `expected`.
        """
        self.assertEqual(expected, self.xmlrpc_resource.log)

    def test_callsUnderlyingImplementation(self):
        # callRemote('method_name') calls that method on the server.
        proxy = self.makeProxy()
        deferred = proxy.callRemote('success')
        return deferred.addCallback(self.checkLog, ['success'])

    def test_passesArguments(self):
        # Extra argument passed to callRemote are passed on to the remote
        # method on the server.
        proxy = self.makeProxy()
        deferred = proxy.callRemote('takesArguments', 2, 3, 5)
        return deferred.addCallback(
            self.checkLog, [('takesArguments', (2, 3, 5))])

    def test_returnsValue(self):
        # The value returned from the remote method is returned by callRemote,
        # albeit as the result of a Deferred.
        proxy = self.makeProxy()
        result = proxy.callRemote('returnsValue', 42)
        result.addCallback(self.assertEqual, 42)
        return result

    def test_methodDoesntExist(self):
        # `callRemote` raises a Fault when we try to call a method that
        # doesn't exist on the remote object.
        proxy = self.makeProxy()
        return self.assertFault(
            proxy.callRemote('doesntExist', 42), 8001, 'doesntExist')

    def test_unpublished(self):
        # An 'unpublished' method is a method on the remote object that is not
        # intended to be called remotely. For Twisted XML-RPC resources, this
        # is a method not prefixed by 'xmlrpc_'. When we call an unpublished
        # method, the proxy behaves as if it doesn't exist.
        proxy = self.makeProxy()
        return self.assertFault(
            proxy.callRemote('unpublished', 42), 8001, 'unpublished')

    def test_unsupportedTypeForParameter(self):
        # Only certain types can go over the wire. If we pass in bad arguments
        # to the proxy, it raises a TypeError.
        proxy = self.makeProxy()
        self.assertRaises(TypeError, proxy.callRemote, 'takesArguments', None)

    def test_returnsUnsupportedType(self):
        # If the remote method returns something that can't go over the wire,
        # the proxy raises a Fault.
        proxy = self.makeProxy()
        return self.assertFault(
            proxy.callRemote('returnsNone'), 8002, "can't serialize output")


class TwistedServer(Server):
    """A test HTTP server that serves an XML-RPC resource.

    Use `getTwistedProxy` to get a real proxy (i.e. a
    `twisted.web.xmlrpc.Proxy`) that points to the resource.
    """

    def __init__(self, xmlrpc_resource):
        super(TwistedServer, self).__init__()
        self.xmlrpc_resource = xmlrpc_resource
        self._service = None

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

    def getTwistedProxy(self):
        return xmlrpc.Proxy(self.get_url())


class InMemoryServer(Server):
    """A test HTTP server that serves an XML-RPC resource."""

    def __init__(self, xmlrpc_resource):
        super(InMemoryServer, self).__init__()
        self.xmlrpc_resource = xmlrpc_resource

    def setUp(self):
        pass

    def get_url(self):
        return None

    def tearDown(self):
        pass

    def getTwistedProxy(self):
        return InMemoryTwistedProxy(self.xmlrpc_resource)


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
