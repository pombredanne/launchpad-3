# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import httplib
import transaction

from zope.security.management import endInteraction

from lazr.restfulclient.errors import HTTPError

from canonical.testing.layers import DatabaseFunctionalLayer
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
        self.branch = self.factory.makeBranch(
            product=self.factory.makeProduct(),
            name='fraggle')
        self.lp = launchpadlib_for("test", self.branch.owner.name)
        transaction.commit()

    def test_delete_branch_without_artifacts(self):
        # A branch unencumbered by links or stacked branches deletes.
        target_branch = self.lp.branches.getByUniqueName(unique_name='fraggle')
        target_branch.delete()

    def test_delete_branch_with_stacked_branch_errors(self):
        # When trying to delete a branch that cannot be deleted, the
        # error is raised across the webservice instead of oopsing.
        stacked_branch = self.factory.makeBranch(stacked_on=self.branch)
        target_branch = self.lp.branches.getByUniqueName(branch.name)
        api_error = self.assertRaises(
            HTTPError,
            branch.delete)
        self.assertIn('Cannot delete', api_error.content)
        self.assertEqual(httplib.FORBIDDEN, api_error.response.status)
