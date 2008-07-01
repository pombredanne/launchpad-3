# Copyright 2008 Canonical Ltd.  All rights reserved.

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.launchpad.webapp.interfaces import AccessLevel
from canonical.launchpad.webapp.authentication import (
    IPersonSet, IPlacelessLoginSource)
from canonical.testing import LaunchpadFunctionalLayer


class LaunchpadLoginSourceTest(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)
        self.login_source = getUtility(IPlacelessLoginSource)
        self.sabdfl = getUtility(IPersonSet).getByName('sabdfl')

    def test_default_access_level(self):
        """By default, if getPrincipal() and getPrincipalByLogin() are given
        no access level, the returned principal will have full access.
        """
        principal = self.login_source.getPrincipal(self.sabdfl.id)
        self.assertEqual(principal.access_level, AccessLevel.WRITE_PRIVATE)
        principal = self.login_source.getPrincipalByLogin(
            self.sabdfl.preferredemail.email)
        self.assertEqual(principal.access_level, AccessLevel.WRITE_PRIVATE)

    def test_given_access_level_is_used(self):
        """If an access level argument is given to getPrincipalByLogin() or
        getPrincipal(), the returned principal will use that.
        """
        principal = self.login_source.getPrincipal(
            self.sabdfl.id, AccessLevel.WRITE_PUBLIC)
        self.assertEqual(principal.access_level, AccessLevel.WRITE_PUBLIC)
        principal = self.login_source.getPrincipalByLogin(
            self.sabdfl.preferredemail.email, AccessLevel.READ_PUBLIC)
        self.assertEqual(principal.access_level, AccessLevel.READ_PUBLIC)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
