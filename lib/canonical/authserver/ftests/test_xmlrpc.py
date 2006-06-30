# Copyright 2004 Canonical Ltd.  All rights reserved.

# TODO:
#  - exercise a bit more of the authUser interface
#  - test createUser (which really requires being able to rollback the changes
#    it makes)

import unittest
import os, sys, time, popen2
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

        # Create a user. 
        self.server.createUser(
                'nobody@example.com',
                SSHADigestEncryptor().encrypt('testpw'),
                'Display Name', []
                )

        # Authenticate a user. This requires two queries - one to retrieve
        # the salt, the other to do the actual auth. This way the auth
        # server never has to see encrypted passwords (probably a pointless
        # security optimization, since the easiest way to attach the auth
        # server would be to have already taken over an application server)
        r1 = self.server.getUser('nobody@example.com')

        loginId = r1['id']
        salt = r1['salt'].decode('base64')
        r2 = self.server.authUser(
                loginId, SSHADigestEncryptor().encrypt('testpw', salt)
                )
        self.failUnlessEqual(r2['displayname'], 'Display Name')
        self.failUnlessEqual(r2['emailaddresses'], ['nobody@example.com'])

    def test_authUser2(self):
        # Just like test_authUser, but passes extra email addresses into
        # createUser like Plone currently is (?)

        # Check that the failure case (no such user or bad passwd) returns {}
        emptyDict = self.server.authUser('invalid@email', '')
        self.assertEqual({}, emptyDict)

        # Create a user. 
        self.server.createUser(
                'nobody@example.com',
                SSHADigestEncryptor().encrypt('testpw'),
                'Display Name', ['nobody@example.com',]
                )

        # Authenticate a user. This requires two queries - one to retrieve
        # the salt, the other to do the actual auth. This way the auth
        # server never has to see encrypted passwords (probably a pointless
        # security optimization, since the easiest way to attach the auth
        # server would be to have already taken over an application server)
        r1 = self.server.getUser('nobody@example.com')

        loginId = r1['id']
        salt = r1['salt'].decode('base64')
        r2 = self.server.authUser(
                loginId, SSHADigestEncryptor().encrypt('testpw', salt)
                )
        self.failUnlessEqual(r2['displayname'], 'Display Name')
        self.failUnlessEqual(r2['emailaddresses'], ['nobody@example.com'])


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

        # Create a user. Note we have to pass in their email address twice
        # (for historical reasons - should refactor one day)
        self.server.createUser(
                'nobody@example.com', # Used to generate the Person.name
                'testpw',
                'Display Name',
                ['nobody@example.com',] # The email addresses stored
                )

        result = self.server.authUser('nobody@example.com', 'testpw')
        self.failUnlessEqual(result['displayname'], 'Display Name')
        self.failUnlessEqual(result['emailaddresses'], ['nobody@example.com'])

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
    """Like XMLRPCv1TestCase, but for the new, simpler, salt-less API."""
    
    def setUp(self):
        LaunchpadTestCase.setUp(self)
        self.tac = AuthserverTacTestSetup()
        self.tac.setUp()
        self.server = xmlrpclib.Server('http://localhost:%s/branch/' 
                                       % _getPort(),
                                       allow_none=True)
        
    def tearDown(self):
        self.tac.tearDown()
        LaunchpadTestCase.tearDown(self)

    def testGetBranchPullQueue(self):
        results = self.server.getBranchPullQueue()
        # We verify that a selection of expected branches are included
        # in the results, each triggering a different pull_url algorithm.
        #   a vcs-imports branch:
        self.assertTrue([14, 'http://escudero.ubuntu.com:680/0000000e']
                        in results)
        #   a pull branch:
        self.assertTrue([15, 'http://example.com/gnome-terminal/main']
                        in results)
        #   a hosted SFTP push branch:
        self.assertTrue([25, '/tmp/sftp-test/branches/00/00/00/19']
                        in results)

    def testStartMirroring(self):
        self.server.startMirroring(18)
        
    def testMirrorComplete(self):
        self.server.mirrorComplete(18, 'rev-1')
        
    def testMirrorCompleteNone(self):
        self.server.mirrorComplete(18, None)
        
    def testMirrorFailedUnicode(self):
        # Ensure that a unicode doesn't cause mirrorFailed to raise an
        # exception.
        self.server.mirrorFailed(18, u'it broke\N{INTERROBANG}')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

