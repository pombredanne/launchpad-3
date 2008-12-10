# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.interface import directlyProvides, directlyProvidedBy
from zope.testing.doctest import DocTestSuite

from canonical.launchpad.interfaces.mail import (
    IWeaklyAuthenticatedPrincipal)
from canonical.launchpad.mail.helpers import (
    ensure_not_weakly_authenticated, IncomingEmailError)
from canonical.launchpad.testing import (
    login_person, TestCaseWithFactory)
from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.webapp.interaction import get_current_principal


class TestEnsureNotWeaklyAuthenticated(TestCaseWithFactory):
    """Test the ensure_not_weakly_authenticated function."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'test@canonical.com')
        self.eric = self.factory.makePerson(name='eric')
        login_person(self.eric)

    def test_normal_user(self):
        # If the current principal doesn't provide
        # IWeaklyAuthenticatedPrincipal, then we are good.
        signed_msg = self.factory.makeSignedMessage()
        ensure_not_weakly_authenticated(signed_msg, 'test case')

    def _setWeakPrincipal(self):
        # Get the current principal to provide IWeaklyAuthenticatedPrincipal
        # this is set when the message is unsigned or the signature doesn't
        # match a key that the person has.
        cur_principal = get_current_principal()
        directlyProvides(
            cur_principal, directlyProvidedBy(cur_principal),
            IWeaklyAuthenticatedPrincipal)

    def test_weakly_authenticated_no_sig(self):
        signed_msg = self.factory.makeSignedMessage()
        self.assertIs(None, signed_msg.signature)
        self._setWeakPrincipal()
        error = self.assertRaises(
            IncomingEmailError,
            ensure_not_weakly_authenticated,
            signed_msg, 'test')
        self.assertEqual(
            "The message you sent included commands to modify the test,\n"
            "but you didn't sign the message with your OpenPGP key.\n",
            error.message)

    def test_weakly_authenticated_with_sig(self):
        signed_msg = self.factory.makeSignedMessage()
        signed_msg.signature = 'fakesig'
        self._setWeakPrincipal()
        error = self.assertRaises(
            IncomingEmailError,
            ensure_not_weakly_authenticated,
            signed_msg, 'test')
        self.assertEqual(
            "The message you sent included commands to modify the test,\n"
            "but your OpenPGP key isn't imported into Launchpad. "
            "Please go to\n"
            "http://launchpad.dev/~eric/+editpgpkeys to import your key.\n",
            error.message)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(DocTestSuite('canonical.launchpad.mail.handlers'))
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite
