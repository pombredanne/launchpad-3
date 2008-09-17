# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0104

import unittest
import xmlrpclib

import pytz

from twisted.application import internet, strports
from twisted.trial.unittest import TestCase as TrialTestCase
from twisted.web import resource, server, xmlrpc

from canonical.authserver.tests.harness import AuthserverTacTestSetup
from canonical.authserver.xmlrpc import LoggingResource
from canonical.config import config
from canonical.functional import XMLRPCTestTransport
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.testing import (
    LaunchpadLayer, LaunchpadFunctionalLayer, TwistedLayer)
from canonical.twistedsupport import suppress_stderr


UTC = pytz.timezone('UTC')


def _getPort():
    portDescription = config.authserver.port
    kind, args, kwargs = strports.parse(portDescription, None)
    assert kind == 'TCP'
    return int(args[0])


class XMLRPCAuthServerTestCase(unittest.TestCase):
    """Base fixture for XMLRPC test case to the AuthServer."""
    layer = LaunchpadLayer
    # Should contain the end-point to test.
    endpoint = ''

    def setUp(self):
        """Set up the XML-RPC server."""
        AuthserverTacTestSetup().setUp()
        self.server = xmlrpclib.Server('http://localhost:%s%s' % (
            _getPort(), self.endpoint))

    def tearDown(self):
        """Tear down the test and reset the database."""
        AuthserverTacTestSetup().tearDown()
        self.layer.force_dirty_database()


class TestLoggingResource(TrialTestCase):

    layer = TwistedLayer

    class TestResource(LoggingResource):
        """An XMLRPC resource that has a method that raises an error."""

        def xmlrpc_good(self, x):
            """Just here to test the XML-RPC fixture."""
            return x

        def xmlrpc_divide_by_zero(self):
            """Deliberately raise an error."""
            1/0

    def setUp(self):
        root = resource.Resource()
        root.putChild('test-resource', self.TestResource())
        site = server.Site(root)
        web_server = internet.TCPServer(0, site)
        web_server.startService()
        self.addCleanup(web_server.stopService)
        host = web_server._port.getHost()
        self.url = 'http://%s:%s/test-resource' % (host.host, host.port)

    def test_tracebackOptionSetForTestRunner(self):
        # For the test runner, include_traceback_in_fault is enabled by
        # default.
        self.assertEqual(True, config.authserver.include_traceback_in_fault)

    def test_fixture(self):
        # Confirm that the fixture is all good.
        client = xmlrpc.Proxy(self.url)
        deferred = client.callRemote('good', 42)
        deferred.addCallback(self.assertEqual, 42)
        return deferred

    def _flushLogs(self, pass_through):
        self.flushLoggedErrors(ZeroDivisionError)
        return pass_through

    @suppress_stderr
    def getFaultString(self, method, *arguments):
        """Call 'method' on the XML-RPC server and fire the fault string it
        makes.
        """
        client = xmlrpc.Proxy(self.url)
        deferred = client.callRemote('divide_by_zero')
        deferred.addBoth(self._flushLogs)
        deferred = self.assertFailure(deferred, xmlrpc.Fault)
        return deferred.addCallback(lambda fault: fault.faultString)

    def test_tracebackInFault(self):
        # The original traceback is stored in the fault string.
        def check_fault_string(fault_string):
            self.assertIn('Original traceback', fault_string)

        deferred = self.getFaultString('divide_by_zero')
        return deferred.addCallback(check_fault_string)

    def test_tracebackNotInFault(self):
        # The original traceback is not in the fault string if the config
        # option is disabled.
        config.push(
            "test", '[authserver]\ninclude_traceback_in_fault: False\n')
        config.authserver.include_traceback_in_fault = False

        def check_fault_string(fault_string):
            self.assertNotIn('Original traceback', fault_string)

        def restore_config(pass_through):
            config.pop("test")
            return pass_through

        deferred = self.getFaultString('divide_by_zero')
        deferred.addCallback(check_fault_string)
        return deferred.addBoth(restore_config)


class XMLRPCv1TestCase(XMLRPCAuthServerTestCase):

    endpoint = '/'

    def test_getUser(self):
        # Check that getUser works, and returns the right contents
        mark_dict = self.server.getUser('mark@hbd.com')
        self.assertEqual('Mark Shuttleworth', mark_dict['displayname'])
        self.assertEqual(['mark@hbd.com'], mark_dict['emailaddresses'])
        self.assert_(mark_dict.has_key('id'))
        self.assert_(mark_dict.has_key('salt'))

        # Check that the salt is base64 encoded
        # FIXME: This is a pretty weak test, because this particular salt is
        #        '' (the sample data specifies no pw for Mark)
        mark_dict['salt'].decode('base64')  # Should raise no errors

        # Check that the failure case (no such user) returns {}
        empty_dict = self.server.getUser('invalid@email')
        self.assertEqual({}, empty_dict)

    def test_authUser(self):
        # Check that the failure case (no such user or bad passwd) returns {}
        empty_dict = self.server.authUser('invalid@email', '')
        self.assertEqual({}, empty_dict)

        # Authenticate a user. This requires two queries - one to retrieve
        # the salt, the other to do the actual auth. This way the auth
        # server never has to see encrypted passwords (probably a pointless
        # security optimization, since the easiest way to attach the auth
        # server would be to have already taken over an application server)
        r1 = self.server.getUser('test@canonical.com')

        loginId = r1['id']
        salt = r1['salt'].decode('base64')
        r2 = self.server.authUser(
                loginId, SSHADigestEncryptor().encrypt('test', salt))
        self.failUnlessEqual(r2['displayname'], 'Sample Person')
        self.failUnless('test@canonical.com' in r2['emailaddresses'])

    def test_authUser2(self):
        # Check that the failure case (no such user or bad passwd) returns {}
        empty_dict = self.server.authUser('invalid@email', '')
        self.assertEqual({}, empty_dict)

        # Authenticate a user. This requires two queries - one to retrieve
        # the salt, the other to do the actual auth. This way the auth
        # server never has to see encrypted passwords (probably a pointless
        # security optimization, since the easiest way to attach the auth
        # server would be to have already taken over an application server)
        r1 = self.server.getUser('test@canonical.com')

        loginId = r1['id']
        salt = r1['salt'].decode('base64')
        r2 = self.server.authUser(
            loginId, SSHADigestEncryptor().encrypt('test', salt))
        self.failUnlessEqual(r2['displayname'], 'Sample Person')
        self.failUnless('test@canonical.com' in r2['emailaddresses'])


class XMLRPCv2TestCase(XMLRPCAuthServerTestCase):
    """Like XMLRPCv1TestCase, but for the new, simpler, salt-less API."""

    endpoint = '/v2/'

    def test_getUser(self):
        # Check that getUser works, and returns the right contents
        mark_dict = self.server.getUser('mark@hbd.com')
        self.assertEqual('Mark Shuttleworth', mark_dict['displayname'])
        self.assertEqual(['mark@hbd.com'], mark_dict['emailaddresses'])
        self.assert_(mark_dict.has_key('id'))

        # Check specifically that there's no 'salt' entry in the user dict.
        self.failIf(mark_dict.has_key('salt'))

        # Check that the failure case (no such user) returns {}
        empty_dict = self.server.getUser('invalid@email')
        self.assertEqual({}, empty_dict)

    def test_authUser(self):
        # Check that the failure case (no such user or bad passwd) returns {}
        empty_dict = self.server.authUser('invalid@email', '')
        self.assertEqual({}, empty_dict)

        result = self.server.authUser('test@canonical.com', 'test')
        self.failUnlessEqual(result['displayname'], 'Sample Person')
        self.failUnless('test@canonical.com' in result['emailaddresses'])


class PrivateXMLRPCAuthServerTestCase(XMLRPCv2TestCase):
    """Like XMLRPCv2TestCase but against the Launchpad private XML-RPC server.
    """
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        self.server = xmlrpclib.ServerProxy(
            'http://xmlrpc-private.launchpad.dev:8087/authserver',
            transport=XMLRPCTestTransport())

    def tearDown(self):
        pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

