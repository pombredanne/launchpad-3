# Copyright 2004 Canonical Ltd.  All rights reserved.

# TODO:
#  - exercise a bit more of the authUser interface
#  - test createUser (which really requires being able to rollback the changes
#    it makes)

import unittest
import os, sys, time, popen2
import xmlrpclib

from twisted.python.util import sibpath
from canonical.launchpad.ftests.harness import LaunchpadTestCase
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor


class XMLRPCTestCase(LaunchpadTestCase):
    # This test requires write access to the current working dir (it writes a
    # twistd.log and twistd.pid (and deletes them), and also the launchpad_test
    # DB created by running make in launchpad's database/schema directory.
    def setUp(self):
        super(XMLRPCTestCase, self).setUp()
        os.system('kill `cat twistd.pid 2> /dev/null` > /dev/null 2>&1')
        cmd = 'twistd -oy %s' % (sibpath(__file__, 'test.tac'),)
        rv = os.system(cmd)
        self.failUnlessEqual(rv, 0)
        self.server = xmlrpclib.Server('http://localhost:9666/')

        # XXX: Wait for twistd to have a chance to start and connect to db.
        #      It'd be cleaner to get a notification of this, rather than
        #      guessing.
        time.sleep(0.1)
    
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

        # Create a user. Note we have to pass in their email address twice
        # (for historical reasons - should refactor one day)
        self.server.createUser(
                'nobody@example.com', # Used to generate the Person.name
                SSHADigestEncryptor().encrypt('testpw'),
                'Display Name',
                ['nobody@example.com',] # The email addresses stored
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

    def tearDown(self):
        pid = int(open('twistd.pid').read())
        ret = os.system('kill `cat twistd.pid`')
        # Wait for it to actually die
        while True:
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(0.1)
        os.remove('twistd.log')
        super(XMLRPCTestCase, self).setUp()
        self.failIf(ret)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XMLRPCTestCase))
    return suite

