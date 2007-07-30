# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for Branches."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from canonical.launchpad.ftests import login, logout, syncUpdate
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, BranchType, CannotDeleteBranch,
    CreateBugParams, IBugSet, ILaunchpadCelebrities, IPersonSet,
    ISpecificationSet)
from canonical.launchpad.database.branch import BranchSet
from canonical.launchpad.database.codeimport import CodeImportSet
from canonical.launchpad.database.product import ProductSet
from canonical.launchpad.database.revision import RevisionSet
from canonical.lp.dbschema import (
    RevisionControlSystems, SpecificationDefinitionStatus)

from canonical.testing import LaunchpadFunctionalLayer

from zope.component import getUtility


class TestBranchDeletion(TestCase):
    """Test the different cases that makes a branch deletable or not."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login('test@canonical.com')
        # Getting database classes directly where necessary to avoid the hastle
        # of worrying about the security contexts.
        self.product = ProductSet().getByName('firefox')
        self.user = getUtility(IPersonSet).getByEmail('test@canonical.com')
        self.branch_set = BranchSet()
        self.branch = BranchSet().new(
            BranchType.HOSTED, 'to-delete', self.user, self.user,
            self.product, None, 'A branch to delete')

    def tearDown(self):
        logout()

    def test_deletable(self):
        """A newly created branch can be deleted without any problems."""
        self.assertEqual(self.branch.canBeDeleted(), True,
                         "A newly created branch should be able to be deleted.")
        BranchSet().delete(self.branch)

    def test_subscriptionDisablesDeletion(self):
        """A branch that has a subscription cannot be deleted."""
        self.branch.subscribe(
            self.user, BranchSubscriptionNotificationLevel.NOEMAIL, None)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch that has a subscription is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, self.branch)

    def test_codeImportDisablesDeletion(self):
        """A branch that has an attached code import can't be deleted."""
        # Branches for code imports must be owned by vcs imports.
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        branch = BranchSet().new(
            BranchType.IMPORTED, 'firefox-import', vcs_imports, vcs_imports,
            self.product, None, 'A firefox import branch')
        code_import = CodeImportSet().new(
            self.user, branch, RevisionControlSystems.SVN,
            'svn://example.com/some/url')
        syncUpdate(code_import)
        self.assertEqual(branch.canBeDeleted(), False,
                         "A branch that has a import is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, branch)

    def test_bugBranchLinkDisablesDeletion(self):
        """A branch linked to a bug cannot be deleted."""
        params = CreateBugParams(
            owner=self.user, title='Firefox bug', comment='blah')
        params.setBugTarget(product=self.product)
        bug = getUtility(IBugSet).createBug(params)
        bug.addBranch(self.branch)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch linked to a bug is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, self.branch)

    def test_specBranchLinkDisablesDeletion(self):
        """A branch linked to a spec cannot be deleted."""
        spec = getUtility(ISpecificationSet).new(
            name='some-spec', title='Some spec', product=self.product,
            owner=self.user, summary='', specurl=None,
            definition_status=SpecificationDefinitionStatus.NEW)
        spec.linkBranch(self.branch)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch linked to a spec is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, self.branch)

    def test_associatedProductSeriesUserBranchDisablesDeletion(self):
        """A branch linked as a user_branch to a product series cannot be
        deleted.
        """
        self.product.development_focus.user_branch = self.branch
        syncUpdate(self.product.development_focus)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch that is a user branch for a product series "
                         "is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, self.branch)

    def test_associatedProductSeriesImportBranchDisablesDeletion(self):
        """A branch linked as an import_branch to a product series cannot
        be deleted.
        """
        self.product.development_focus.import_branch = self.branch
        syncUpdate(self.product.development_focus)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch that is an import branch for a product "
                         "series is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, self.branch)

    def test_revisionsDisableDeletion(self):
        """A branch that has some revisions cannot be deleted."""
        revision = RevisionSet().new(
            revision_id='some-unique-id', log_body='commit message',
            revision_date=None, revision_author='ddaa@localhost',
            owner=self.user, parent_ids=[], properties=None)
        self.branch.createBranchRevision(0, revision)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch that has a revision is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, self.branch)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
