# Copyright 2004 Canonical Ltd.  All rights reserved.

# TODO:
#  - exercise a bit more of the authUser interface
#  - test createUser

import unittest
import os
import time
import xmlrpclib

from twisted.python.util import sibpath


class XMLRPCTestCase(unittest.TestCase):
    # This test requires write access to the current working dir (it writes a
    # twistd.log and twistd.pid (and deletes them), and also the launchpad_test
    # DB created by running make in launchpad's database/schema directory.
    def setUp(self):
        # Start a twistd process using the test.tac in the ftests directory
        ret = os.system('twistd -oy ' + sibpath(__file__, 'test.tac'))
        self.failUnlessEqual(0, ret)
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

    def tearDown(self):
        # Kill the twistd process
        ret = os.system('kill `cat twistd.pid`')
        os.remove('twistd.log')
        self.failIf(ret)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XMLRPCTestCase))
    return suite

