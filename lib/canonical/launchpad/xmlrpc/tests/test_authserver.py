# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the internal codehosting API."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.publisher.xmlrpc import TestRequest

from canonical.launchpad.interfaces import IPrivateApplication
from lp.testing import TestCaseWithFactory
from canonical.launchpad.xmlrpc import faults
from canonical.launchpad.xmlrpc.authserver import AuthServerAPIView
from canonical.testing.layers import DatabaseFunctionalLayer

class GetUserAndSSHKeysTests(TestCaseWithFactory):
    """Tests for the implementation of `IAuthServer.getUserAndSSHKeys`.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        private_root = getUtility(IPrivateApplication)
        self.authserver = AuthServerAPIView(
            private_root.authserver, TestRequest())

    def assertFaultEqual(self, expected_fault, observed_fault):
        """Assert that `expected_fault` equals `observed_fault`."""
        self.assertIsInstance(observed_fault, faults.LaunchpadFault)
        self.assertEqual(expected_fault.faultCode, observed_fault.faultCode)
        self.assertEqual(
            expected_fault.faultString, observed_fault.faultString)

    def test_user_not_found(self):
        # getUserAndSSHKeys returns the NoSuchPersonWithName fault if there is
        # no Person of the given name.
        self.assertFaultEqual(
            faults.NoSuchPersonWithName('no-one'),
            self.authserver.getUserAndSSHKeys('no-one'))

    def test_user_no_keys(self):
        # getUserAndSSHKeys returns a dict with keys ['id', 'name', 'keys'].
        # 'keys' refers to a list of SSH public keys in LP, which is empty for
        # a freshly created user.
        new_person = self.factory.makePerson()
        self.assertEqual(
            dict(id=new_person.id, name=new_person.name, keys=[]),
            self.authserver.getUserAndSSHKeys(new_person.name))

    def test_user_with_keys(self):
        # For a user with registered SSH keys, getUserAndSSHKeys returns the
        # name of the key type (RSA or DSA) and the text of the keys under
        # 'keys' in the dict.
        new_person = self.factory.makePerson()
        key = self.factory.makeSSHKey(person=new_person)
        self.assertEqual(
            dict(id=new_person.id, name=new_person.name,
                 keys=[(key.keytype.title, key.keytext)]),
            self.authserver.getUserAndSSHKeys(new_person.name))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
