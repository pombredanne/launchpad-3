# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for edit view permissions unit tests."""

__metaclass__ = type


import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    login_person,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import IPersonSet
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class EditViewPermissionBase(TestCaseWithFactory):
    """Tests for permissions access the +edit page on the target."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(EditViewPermissionBase, self).setUp()
        self.setupTarget()
        self.registry_admin = self.factory.makePerson(name='registry-admin')
        celebs = getUtility(ILaunchpadCelebrities)
        login_person(celebs.registry_experts.teamowner)
        celebs.registry_experts.addMember(self.registry_admin,
                                          self.registry_admin)
        self.request = LaunchpadTestRequest()

    def setupTarget(self):
        """Set up the target context for the test suite."""
        self.target = self.factory.makePerson(name='target-person')

    def test_anon_cannot_edit(self):
        login(ANONYMOUS)
        view = create_initialized_view(self.target, '+edit')
        self.assertFalse(check_permission('launchpad.Edit', view))

    def test_arbitrary_user_cannot_edit(self):
        person = self.factory.makePerson(name='the-dude')
        login_person(person)
        view = create_initialized_view(self.target, '+edit')
        self.assertFalse(check_permission('launchpad.Edit', view))

    def test_admin_can_edit(self):
        admin = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        login_person(admin)
        view = create_initialized_view(self.target, '+edit')
        self.assertTrue(check_permission('launchpad.Edit', view))

    def test_registry_expert_cannot_edit(self):
        login_person(self.registry_admin)
        view = create_initialized_view(self.target, '+edit')
        self.assertFalse(check_permission('launchpad.Edit', view))


class PersonEditViewPermissionTestCase(EditViewPermissionBase):
    """Tests for permissions to access person +edit page."""
    def test_arbitrary_user_can_edit_her_own_data(self):
        login_person(self.target)
        view = create_initialized_view(self.target, '+edit')
        self.assertTrue(check_permission('launchpad.Edit', view))


class ProductEditViewPermissionTestCase(EditViewPermissionBase):
    """Tests for permissions to access prodcut +edit page."""
    def setupTarget(self):
        self.target = self.factory.makeProduct()


class ProjectEditViewPermissionTestCase(EditViewPermissionBase):
    """Tests for permissions to access prodcut +edit page."""
    def setupTarget(self):
        self.target = self.factory.makeProject()


class DistributionEditViewPermissionTestCase(EditViewPermissionBase):
    """Tests for permissions to access prodcut +edit page."""
    def setupTarget(self):
        self.target = self.factory.makeDistribution()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    return suite


if __name__ == '__main__':
    unittest.main()
