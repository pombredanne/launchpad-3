# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests related to ILaunchpadRoot."""

__metaclass__ = type

import unittest


from zope.component import getUtility
from zope.security.checker import selectChecker

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.launchpad.webapp.authorization import check_permission
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.registry.interfaces.person import IPersonSet
from lp.testing import login_person, TestCaseWithFactory
from lp.testing.views import create_view


class LaunchpadRootPermissionTest(TestCaseWithFactory):
    """Test for the ILaunchpadRoot permission"""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.root = getUtility(ILaunchpadRoot)
        self.admin = getUtility(IPersonSet).getByEmail(
            'foo.bar@canonical.com')

    def test_anonymous_cannot_edit(self):
        self.failIf(check_permission('launchpad.Edit', self.root),
            "Anonymous user shouldn't have launchpad.Edit on ILaunchpadRoot")

    def test_regular_user_cannot_edit(self):
        login_person(self.factory.makePersonNoCommit())
        self.failIf(check_permission('launchpad.Edit', self.root),
            "Regular users shouldn't have launchpad.Edit on ILaunchpadRoot")

    def test_registry_expert_can_edit(self):
        login_person(self.admin)
        expert = self.factory.makePersonNoCommit()
        getUtility(ILaunchpadCelebrities).registry_experts.addMember(
            expert, self.admin)
        login_person(expert)
        self.failUnless(check_permission('launchpad.Edit', self.root),
            "Registry experts should have launchpad.Edit on ILaunchpadRoot")

    def test_admins_can_edit(self):
        login_person(self.admin)
        self.failUnless(check_permission('launchpad.Edit', self.root),
            "Admins should have launchpad.Edit on ILaunchpadRoot")

    def test_featured_projects_view_requires_edit(self):
        view = create_view(self.root, '+featuredprojects')
        checker = selectChecker(view)
        self.assertEquals('launchpad.Edit', checker.permission_id('__call__'))



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

