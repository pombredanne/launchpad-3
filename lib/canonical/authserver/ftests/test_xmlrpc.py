# Copyright 2004 Canonical Ltd.  All rights reserved.

# TODO:
#  - exercise a bit more of the authUser interface

import unittest
import xmlrpclib

from twisted.application import strports
from canonical.authserver.ftests.harness import AuthserverTacTestSetup
from canonical.launchpad.ftests.harness import LaunchpadTestCase
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.config import config

def _getPort():
    portDescription = config.authserver.port
    kind, args, kwargs = strports.parse(portDescription, None)
    assert kind == 'TCP'
    return int(args[0])


class XMLRPCv1TestCase(LaunchpadTestCase):
    def setUp(self):
        LaunchpadTestCase.setUp(self)
        AuthserverTacTestSetup().setUp()
        self.server = xmlrpclib.Server('http://localhost:%s/' % _getPort())
    
    def tearDown(self):
        AuthserverTacTestSetup().tearDown()
        LaunchpadTestCase.tearDown(self)

    def test_getUser(self):
        # Check that getUser works, and returns the right contents
        markDict = self.server.getUser('mark@hbd.com')
        self.assertEqual('Mark Shuttleworth', markDict['displayname'])
        self.assertEqual(['mark@hbd.com'], markDict['emailaddresses'])
        self.assert_(markDict.has_key('id'))
        self.assert_(markDict.has_key('salt'))
        
        # Check that the salt is base64 encoded
        # FIXME: This is a pretty weak test, because this particular salt is ''
        #        (the sample data specifies no pw for Mark)
        markDict['salt'].decode('base64')  # Should raise no errors

        # Check that the failure case (no such user) returns {}
        emptyDict = self.server.getUser('invalid@email')
        self.assertEqual({}, emptyDict)

    def test_authUser(self):
        # Check that the failure case (no such user or bad passwd) returns {}
        emptyDict = self.server.authUser('invalid@email', '')
        self.assertEqual({}, emptyDict)

        # Authenticate a user. This requires two queries - one to retrieve
        # the salt, the other to do the actual auth. This way the auth
        # server never has to see encrypted passwords (probably a pointless
        # security optimization, since the easiest way to attach the auth
        # server would be to have already taken over an application server)
        r1 = self.server.getUser('test@canonical.com')

        loginId = r1['id']
        salt = r1['salt'].decode('base64')
        r2 = self.server.authUser(
                loginId, SSHADigestEncryptor().encrypt('test', salt)
                )
        self.failUnlessEqual(r2['displayname'], 'Sample Person')
        self.failUnless('test@canonical.com' in r2['emailaddresses'])

    def test_authUser2(self):
        # Check that the failure case (no such user or bad passwd) returns {}
        emptyDict = self.server.authUser('invalid@email', '')
        self.assertEqual({}, emptyDict)

        # Authenticate a user. This requires two queries - one to retrieve
        # the salt, the other to do the actual auth. This way the auth
        # server never has to see encrypted passwords (probably a pointless
        # security optimization, since the easiest way to attach the auth
        # server would be to have already taken over an application server)
        r1 = self.server.getUser('test@canonical.com')

        loginId = r1['id']
        salt = r1['salt'].decode('base64')
        r2 = self.server.authUser(
                loginId, SSHADigestEncryptor().encrypt('test', salt)
                )
        self.failUnlessEqual(r2['displayname'], 'Sample Person')
        self.failUnless('test@canonical.com' in r2['emailaddresses'])

    def test_getSSHKeys(self):
        # Unknown users have no SSH keys, of course.
        self.assertEqual([], self.server.getSSHKeys('unknown@user'))

        # Check that the SSH key in the sample data can be retrieved
        # successfully.
        keys = self.server.getSSHKeys('test@canonical.com')

        # There should only be one key for this user.
        self.assertEqual(1, len(keys))

        # Check the keytype is being returned correctly.
        keytype, keytext = keys[0]
        self.assertEqual('DSA', keytype)


class XMLRPCv2TestCase(LaunchpadTestCase):
    """Like XMLRPCv1TestCase, but for the new, simpler, salt-less API."""
    def setUp(self):
        LaunchpadTestCase.setUp(self)
        AuthserverTacTestSetup().setUp()
        self.server = xmlrpclib.Server('http://localhost:%s/v2/' % _getPort())
    
    def tearDown(self):
        AuthserverTacTestSetup().tearDown()
        LaunchpadTestCase.tearDown(self)

    def test_getUser(self):
        # Check that getUser works, and returns the right contents
        markDict = self.server.getUser('mark@hbd.com')
        self.assertEqual('Mark Shuttleworth', markDict['displayname'])
        self.assertEqual(['mark@hbd.com'], markDict['emailaddresses'])
        self.assert_(markDict.has_key('id'))

        # Check specifically that there's no 'salt' entry in the user dict.
        self.failIf(markDict.has_key('salt'))
        
        # Check that the failure case (no such user) returns {}
        emptyDict = self.server.getUser('invalid@email')
        self.assertEqual({}, emptyDict)

    def test_authUser(self):
        # Check that the failure case (no such user or bad passwd) returns {}
        emptyDict = self.server.authUser('invalid@email', '')
        self.assertEqual({}, emptyDict)

        result = self.server.authUser('test@canonical.com', 'test')
        self.failUnlessEqual(result['displayname'], 'Sample Person')
        self.failUnless('test@canonical.com' in result['emailaddresses'])

    def test_getBranchesForUser(self):
        # XXX: justs check that it doesn't error, should also check the result.
        self.server.getBranchesForUser(12)

    def test_fetchProductID(self):
        self.assertEqual(4, self.server.fetchProductID('firefox'))
        self.assertEqual('', self.server.fetchProductID('xxxxx'))

    def test_createBranch(self):
        # XXX: justs check that it doesn't error, should also check the result.
        self.server.createBranch(12, 4, 'new-branch')


class BranchAPITestCase(LaunchpadTestCase):
    """Tests for the branch details API."""
    
    def setUp(self):
        LaunchpadTestCase.setUp(self)
        self.tac = AuthserverTacTestSetup()
        self.tac.setUp()
        self.server = xmlrpclib.Server('http://localhost:%s/branch/' 
                                       % _getPort())
        
    def tearDown(self):
        self.tac.tearDown()
        LaunchpadTestCase.tearDown(self)

    def testGetBranchPullQueue(self):
        results = self.server.getBranchPullQueue()
        # Check whether one of the expected branches is in the results:
        self.assertTrue([15, 'http://example.com/gnome-terminal/main']
                        in results)

    def testStartMirroring(self):
        self.server.startMirroring(18)
        
    def testMirrorComplete(self):
        self.server.mirrorComplete(18, 'rev-1')
        
    def testMirrorFailedUnicode(self):
        # Ensure that a unicode doesn't cause mirrorFailed to raise an
        # exception.
        self.server.mirrorFailed(18, u'it broke\N{INTERROBANG}')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

