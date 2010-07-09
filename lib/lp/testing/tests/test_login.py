# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the login helpers."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.interaction import get_current_principal
from canonical.launchpad.webapp.interfaces import IOpenLaunchBag
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import is_logged_in, login_person, logout
from lp.testing import TestCaseWithFactory


class TestLoginHelpers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def assertLoggedIn(self, person):
        """Assert that 'person' is logged in."""
        # XXX: JonathanLange 2010-07-09: I don't really know the canonical way
        # of asking for "the logged-in person", so instead I'm testing all the
        # ways that I can tell.
        self.assertEqual(person, get_current_principal().person)
        self.assertEqual(person, getUtility(IOpenLaunchBag).user)

    def test_not_logged_in(self):
        # After logout has been called, we are not logged in.
        logout()
        self.assertEqual(False, is_logged_in())

    def test_logout_twice(self):
        # Logging out twice don't harm anybody none.
        logout()
        logout()
        self.assertEqual(False, is_logged_in())

    def test_logged_in(self):
        # After login has been called, we are logged in.
        login_person(self.factory.makePerson())
        self.assertEqual(True, is_logged_in())

    def test_login_person_actually_logs_in(self):
        person = self.factory.makePerson()
        login_person(person)
        self.assertLoggedIn(person)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
