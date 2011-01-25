# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import httplib
import transaction

from zope.component import getUtility

from lazr.restfulclient.errors import HTTPError

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.branch import IBranchSet
from lp.testing import (
    launchpadlib_for,
    login_person,
    logout,
    TestCaseWithFactory,
    )


class TestBranchDeletes(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBranchDeletes, self).setUp()
        self.branch_owner = self.factory.makePerson(name='jimhenson')
        self.branch = self.factory.makeBranch(
            owner=self.branch_owner,
            product=self.factory.makeProduct(name='fraggle'),
            name='rock')
        self.lp = launchpadlib_for("test", self.branch.owner.name)

    def test_delete_branch_without_artifacts(self):
        # A branch unencumbered by links or stacked branches deletes.
        target_branch = self.lp.branches.getByUniqueName(
            unique_name='~jimhenson/fraggle/rock')
        target_branch.lp_delete()
        
        login_person(self.branch_owner)
        branch_set = getUtility(IBranchSet)
        self.assertIs(
            None,
            branch_set.getByUniqueName('~jimhenson/fraggle/rock'))

    def test_delete_branch_with_stacked_branch_errors(self):
        # When trying to delete a branch that cannot be deleted, the
        # error is raised across the webservice instead of oopsing.
        login_person(self.branch_owner)
        stacked_branch = self.factory.makeBranch(
            stacked_on=self.branch,
            owner=self.branch_owner)
        logout()
        target_branch = self.lp.branches.getByUniqueName(
            unique_name='~jimhenson/fraggle/rock')
        api_error = self.assertRaises(
            HTTPError,
            target_branch.lp_delete)
        self.assertIn('Cannot delete', api_error.content)
        self.assertEqual(httplib.BAD_REQUEST, api_error.response.status)
