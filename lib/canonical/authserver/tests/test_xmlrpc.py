# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0104

# TODO:
#  - exercise a bit more of the authUser interface

import datetime
import unittest
import xmlrpclib

import pytz

from twisted.application import internet, strports
from twisted.trial.unittest import TestCase as TrialTestCase
from twisted.web import resource, server, xmlrpc

from canonical.authserver.interfaces import WRITABLE
from canonical.authserver.tests.harness import AuthserverTacTestSetup
from canonical.authserver.xmlrpc import LoggingResource
from canonical.config import config
from canonical.functional import XMLRPCTestTransport
from canonical.launchpad.interfaces import BranchType
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


class SSHKeysTestMixin:
    """Test the getSSHKeys method.

    This method is present in V1 and V2 interface.
    """

    def test_getSSHKeys(self):
        # Unknown users have no SSH keys, of course.
        self.assertEqual([], self.server.getSSHKeys('nosuchuser'))

        # Check that the SSH key in the sample data can be retrieved
        # successfully.
        keys = self.server.getSSHKeys('test@canonical.com')

        # There should only be one key for this user.
        self.assertEqual(1, len(keys))

        # Check the keytype is being returned correctly.
        keytype, keytext = keys[0]
        self.assertEqual('DSA', keytype)


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

class XMLRPCv1TestCase(XMLRPCAuthServerTestCase, SSHKeysTestMixin):

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


class XMLRPCv2TestCase(XMLRPCAuthServerTestCase, SSHKeysTestMixin):
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


class XMLRPCHostedBranchStorage(XMLRPCAuthServerTestCase):
    """Tests for the XML-RPC implementation of IHostedBranchStorage."""

    endpoint = '/v2/'

    def test_getBranchesForUser(self):
        # XXX: Andrew Bennetts 2005-12-13:
        # Justs check that it doesn't error, should also check the result.
        self.server.getBranchesForUser(12)

    def test_fetchProductID(self):
        self.assertEqual(4, self.server.fetchProductID('firefox'))
        self.assertEqual('', self.server.fetchProductID('xxxxx'))

    def test_createBranch(self):
        # XXX Andrew Bennetts, 2007-01-24:
        # This test just checks that createBranch doesn't error.  This test
        # should also check the result.
        self.server.createBranch(12, 'name12', 'firefox', 'new-branch')

    def test_requestMirror(self):
        # XXX Andrew Bennetts, 2007-01-24:
        # Only checks that requestMirror doesn't error. Should instead
        # check the result.

        # This is a user who has launchpad.View permissions on the hosted
        # branch.
        user_id = 1
        hosted_branch_id = 25
        self.server.requestMirror(user_id, hosted_branch_id)

    def test_getBranchInformation(self):
        # Don't test the full range of values for getBranchInformation, as we
        # rely on the database tests to do that. This test just confirms it's
        # all hooked up correctly.
        branch_id, permissions = self.server.getBranchInformation(
            12, 'name12', 'gnome-terminal', 'pushed')
        self.assertEqual(25, branch_id)
        self.assertEqual(WRITABLE, permissions)

    def test_getDefaultStackedOnBranch(self):
        # We can get the default stacked-on branch of a project, given a
        # project name.
        #
        # The 'evolution' project has a default stacked branch in the sample
        # data.
        branch = self.server.getDefaultStackedOnBranch('evolution')
        self.assertEqual('~vcs-imports/evolution/main', branch)

    def test_getDefaultStackedOnBranchWhenEmpty(self):
        # If there is no default stacked-on branch, we'll get an empty string.
        branch = self.server.getDefaultStackedOnBranch('+junk')
        self.assertEqual('', branch)
        # The 'gnome-terminal' project has no default stacked branch.
        branch = self.server.getDefaultStackedOnBranch('gnome-terminal')
        self.assertEqual('', branch)


class BranchAPITestCase(XMLRPCAuthServerTestCase):
    """Tests for the branch details API."""

    endpoint = '/branch/'

    def testGetBranchPullQueue(self):
        results = self.server.getBranchPullQueue(BranchType.MIRRORED.name)
        # Check whether one of the expected branches is in the results:
        self.assertTrue(
            [15, 'http://example.com/gnome-terminal/main',
             u'name12/gnome-terminal/main']
            in results)

    def testStartMirroring(self):
        self.server.startMirroring(18)
        # The branch puller script will pull private branches. We need to
        # confirm that it can do so without triggering Zope security
        # restrictions.
        # Branch 29 is a private branch in the sample data.
        self.server.startMirroring(29)

    def testMirrorComplete(self):
        self.server.startMirroring(18)
        self.server.mirrorComplete(18, 'rev-1')
        # See comment in testStartMirroring.
        self.server.startMirroring(29)
        self.server.mirrorComplete(29, 'rev-1')

    def testMirrorFailedUnicode(self):
        # Ensure that a unicode doesn't cause mirrorFailed to raise an
        # exception.
        self.server.mirrorFailed(18, u'it broke\N{INTERROBANG}')
        # See comment in testStartMirroring.
        self.server.mirrorFailed(29, u'it broke\N{INTERROBANG}')

    def testRecordSuccess(self):
        started = datetime.datetime(2007, 07, 05, 19, 32, 1, tzinfo=UTC)
        completed = datetime.datetime(2007, 07, 05, 19, 34, 24, tzinfo=UTC)
        started_tuple = tuple(started.utctimetuple())
        completed_tuple = tuple(completed.utctimetuple())
        self.server.recordSuccess(
            'test-recordsuccess', 'vostok', started_tuple, completed_tuple)


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

