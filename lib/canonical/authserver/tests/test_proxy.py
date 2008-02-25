# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the in-memory `ServerProxy` objects."""

__metaclass__ = type

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

    def xmlrpc_returnsValue(self, value):
        return value

    def xmlrpc_success(self):
        self.log.append('success')
        return ''

    def xmlrpc_takesArguments(self, *args):
        self.log.append(('takesArguments', args))
        return ''


class TestInMemoryProxy(unittest.TestCase):

    layer = TwistedLayer

    def setUp(self):
        self.xmlrpc_resource = MockXMLRPCObject()
        self.server = self.server_factory(self.xmlrpc_resource)
        self.server.setUp()

    def tearDown(self):
        self.server.tearDown()

    def makeProxy(self):
        return self.server.getProxy()

    def checkLog(self, ignored, expected):
        self.assertEqual(expected, self.xmlrpc_resource.log)

    def test_callsUnderlyingImplementation(self):
        proxy = self.makeProxy()
        deferred = proxy.callRemote('success')
        return deferred.addCallback(self.checkLog, ['success'])

    def test_passesArguments(self):
        proxy = self.makeProxy()
        deferred = proxy.callRemote('takesArguments', 2, 3, 5)
        return deferred.addCallback(
            self.checkLog, [('takesArguments', (2, 3, 5))])

    def test_returnsValue(self):
        proxy = self.makeProxy()
        result = proxy.callRemote('returnsValue', 42)
        result.addCallback(self.assertEqual, 42)
        return result

    # - Method doesn't exist
    # - Method exists but isn't "published".
    # - Unsupported types explode properly


class TwistedServer(Server):

    def __init__(self, xmlrpc_resource):
        self.xmlrpc_resource = xmlrpc_resource
        self._service = None

    def setUp(self):
        root = resource.Resource()
        root.putChild('xmlrpc', self.xmlrpc_resource)
        site = server.Site(root)
        self._service = strports.service('tcp:0', site)
        self._service.startService()

    def get_url(self):
        return 'http://localhost:%s/xmlrpc' % (self._service._port.getHost().port)

    def tearDown(self):
        self._service.stopService()

    def getProxy(self):
        return xmlrpc.Proxy(self.get_url())


class InMemoryServer(Server):

    def __init__(self, xmlrpc_resource):
        self.xmlrpc_resource = xmlrpc_resource

    def setUp(self):
        pass

    def get_url(self):
        return None

    def tearDown(self):
        pass

    def getProxy(self):
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
