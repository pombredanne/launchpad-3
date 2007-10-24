# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for Branches."""

__metaclass__ = type

from datetime import datetime
from pytz import UTC
import transaction
from unittest import TestCase, TestLoader

from canonical.codehosting.tests.helpers import BranchTestCase
from canonical.config import config
from canonical.launchpad.ftests import ANONYMOUS, login, logout, syncUpdate
from canonical.launchpad.interfaces import (
    BranchListingSort, BranchSubscriptionNotificationLevel, BranchType,
    CannotDeleteBranch, CreateBugParams, IBranchSet, IBugSet,
    ILaunchpadCelebrities, IPersonSet, IProductSet, ISpecificationSet,
    InvalidBranchMergeProposal, PersonCreationRationale,
    RevisionControlSystems, SpecificationDefinitionStatus)
from canonical.launchpad.database.branch import BranchSet
from canonical.launchpad.database.codeimport import CodeImportSet
from canonical.launchpad.database.product import ProductSet
from canonical.launchpad.database.revision import RevisionSet

from canonical.testing import LaunchpadFunctionalLayer, LaunchpadZopelessLayer

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy


class TestBranchDeletion(TestCase):
    """Test the different cases that makes a branch deletable or not."""

    layer = LaunchpadZopelessLayer

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
                         "A newly created branch should be able to be "
                         "deleted.")
        branch_id = self.branch.id
        branch_set = BranchSet()
        branch_set.delete(self.branch)
        self.assert_(branch_set.get(branch_id) is None,
                     "The branch has not been deleted.")

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

    def test_revisionsDeletable(self):
        """A branch that has some revisions can be deleted."""
        # We want the changes done in the setup to stay around, and by
        # default the switchDBUser aborts the transaction.
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
        revision = RevisionSet().new(
            revision_id='some-unique-id', log_body='commit message',
            revision_date=None, revision_author='ddaa@localhost',
            owner=self.user, parent_ids=[], properties=None)
        self.branch.createBranchRevision(0, revision)
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.launchpad.dbuser)
        self.assertEqual(self.branch.canBeDeleted(), True,
                         "A branch that has a revision is deletable.")
        unique_name = self.branch.unique_name
        BranchSet().delete(self.branch)
        self.assertEqual(BranchSet().getByUniqueName(unique_name), None,
                         "Branch was not deleted.")

    def test_landingTargetDisablesDeletion(self):
        """A branch with a landing target cannot be deleted."""
        target_branch = BranchSet().new(
            BranchType.HOSTED, 'landing-target', self.user, self.user,
            self.product, None)
        self.branch.addLandingTarget(self.user, target_branch)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch with a landing target is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, self.branch)

    def test_landingCandidateDisablesDeletion(self):
        """A branch with a landing candidate cannot be deleted."""
        source_branch = BranchSet().new(
            BranchType.HOSTED, 'landing-candidate', self.user, self.user,
            self.product, None)
        source_branch.addLandingTarget(self.user, self.branch)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch with a landing candidate is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, self.branch)

    def test_dependentBranchDisablesDeletion(self):
        """A branch that is a dependent branch cannot be deleted."""
        source_branch = BranchSet().new(
            BranchType.HOSTED, 'landing-candidate', self.user, self.user,
            self.product, None)
        target_branch = BranchSet().new(
            BranchType.HOSTED, 'landing-target', self.user, self.user,
            self.product, None)
        source_branch.addLandingTarget(self.user, target_branch, self.branch)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch with a dependent target is not deletable.")
        self.assertRaises(CannotDeleteBranch, BranchSet().delete, self.branch)


class BranchAddLandingTarget(TestCase):
    """Exercise all the code paths for adding a landing target."""
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        login(ANONYMOUS)
        self.branch_set = BranchSet()
        self.product = getUtility(IProductSet).getByName('firefox')

        self.user = getUtility(IPersonSet).getByName('no-priv')
        self.source = self.branch_set.new(
            BranchType.HOSTED, 'source-branch', self.user, self.user,
            self.product, None)
        self.target = self.branch_set.new(
            BranchType.HOSTED, 'target-branch', self.user, self.user,
            self.product, None)
        self.dependent = self.branch_set.new(
            BranchType.HOSTED, 'dependent-branch', self.user, self.user,
            self.product, None)

    def tearDown(self):
        logout()

    def test_junkSource(self):
        """Junk branches cannot be used as a source for merge proposals."""
        self.source.product = None
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target)

    def test_targetProduct(self):
        """The product of the target branch must match the product of the
        source branch.
        """
        self.target.product = None
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target)

        self.target.product = getUtility(IProductSet).getByName('bzr')
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target)

    def test_targetIsABranch(self):
        """The target of must be a branch."""
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.product)

    def test_targetMustNotBeTheSource(self):
        """The target and source branch cannot be the same."""
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.source)

    def test_dependentIsABranch(self):
        """The dependent branch, if it is there, must be a branch."""
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, dependent_branch=self.product)

    def test_dependentBranchSameProduct(self):
        """The dependent branch, if it is there, must be for the same product.
        """
        self.dependent.product = None
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.dependent)

        self.dependent.product = getUtility(IProductSet).getByName('bzr')
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.dependent)

    def test_dependentMustNotBeTheSource(self):
        """The target and source branch cannot be the same."""
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.source)

    def test_dependentMustNotBeTheTarget(self):
        """The target and source branch cannot be the same."""
        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.target)

    def test_existingMergeProposal(self):
        """If there is an existing merge proposal for the source and target
        branch pair, then another landing target specifying the same pair
        raises.
        """
        proposal = self.source.addLandingTarget(
            self.user, self.target, self.dependent)

        self.assertRaises(
            InvalidBranchMergeProposal, self.source.addLandingTarget,
            self.user, self.target, self.dependent)

    def test_attributeAssignment(self):
        """Smoke test to make sure the assignments are there."""
        whiteboard = u"Some whiteboard"
        proposal = self.source.addLandingTarget(
            self.user, self.target, self.dependent, whiteboard)
        self.assertEqual(proposal.registrant, self.user)
        self.assertEqual(proposal.source_branch, self.source)
        self.assertEqual(proposal.target_branch, self.target)
        self.assertEqual(proposal.dependent_branch, self.dependent)
        self.assertEqual(proposal.whiteboard, whiteboard)


class BranchDateLastModified(BranchTestCase):
    """Exercies the situations where date_last_modifed is udpated."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        BranchTestCase.setUp(self)
        login('test@canonical.com')

    def tearDown(self):
        logout()
        BranchTestCase.tearDown(self)

    def test_initialValue(self):
        """Initially the date_last_modifed is the date_created."""
        branch = self.makeBranch()
        self.assertEqual(branch.date_last_modified, branch.date_created)

    def test_bugBranchLinkUpdates(self):
        """Linking a branch to a bug updates the last modified time."""
        date_created = datetime(2000, 1, 1, 12, tzinfo=UTC)
        branch = self.makeBranch(date_created=date_created)
        self.assertEqual(branch.date_last_modified, date_created)

        params = CreateBugParams(
            owner=branch.owner, title='A bug', comment='blah')
        params.setBugTarget(product=branch.product)
        bug = getUtility(IBugSet).createBug(params)

        bug.addBranch(branch)
        self.assertTrue(branch.date_last_modified > date_created,
                        "Date last modified was not updated.")

    def test_specBranchLinkUpdates(self):
        """Linking a branch to a spec updates the last modified time."""
        date_created = datetime(2000, 1, 1, 12, tzinfo=UTC)
        branch = self.makeBranch(date_created=date_created)
        self.assertEqual(branch.date_last_modified, date_created)

        spec = getUtility(ISpecificationSet).new(
            name='some-spec', title='Some spec', product=branch.product,
            owner=branch.owner, summary='', specurl=None,
            definition_status=SpecificationDefinitionStatus.NEW)
        spec.linkBranch(branch)
        self.assertTrue(branch.date_last_modified > date_created,
                        "Date last modified was not updated.")

    def test_revisionsUpdateModifedTime(self):
        """A branch that gets a new revision is considered modified."""
        date_created = datetime(2000, 1, 1, 12, tzinfo=UTC)
        branch = self.makeBranch(date_created=date_created)
        self.assertEqual(branch.date_last_modified, date_created)
        transaction.commit()

        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
        revision = RevisionSet().new(
            revision_id='some-unique-id', log_body='commit message',
            revision_date=None, revision_author='ddaa@localhost',
            owner=branch.owner, parent_ids=[], properties=None)
        branch.createBranchRevision(0, revision)
        transaction.commit()
        LaunchpadZopelessLayer.switchDbUser(config.launchpad.dbuser)

        self.assertTrue(branch.date_last_modified > date_created,
                        "Date last modified was not updated.")


class BranchSorting(TestCase):
    """Test cases for the sort_by option of BranchSet getBranch* methods."""

    layer = LaunchpadZopelessLayer

    def createPersonWithTwoBranches(self):
        """Create a person and two branches that belong to that person."""
        new_person, email = getUtility(IPersonSet).createPersonAndEmail(
            "test@example.com",
            PersonCreationRationale.OWNER_CREATED_LAUNCHPAD)

        branch_set = getUtility(IBranchSet)
        branch_a = branch_set.new(
            BranchType.MIRRORED, "a", new_person, new_person, None,
            "http://bzr.example.com/a")
        branch_b = branch_set.new(
            BranchType.MIRRORED, "b", new_person, new_person, None,
            "http://bzr.example.com/b")

        return new_person, branch_a, branch_b

    def assertEqualByID(self, first, second):
        """Compare two lists of database objects by id."""
        # XXX: 2007-10-22 MichaelHudson bug=154016: This is only needed
        # because getBranchesForPerson queries the BranchWithSortKeys table
        # and we want to compare the results with objects from the Branch
        # table.  This method can be removed when we can get rid of
        # BranchWithSortKeys.
        self.assertEqual([a.id for a in first], [b.id for b in second])

    def xmas(self, year):
        """Create a UTC datetime for Christmas of the given year."""
        return datetime(year=year, month=12, day=25, tzinfo=UTC)

    def test_sortByRecentChanges(self):
        """Test the MOST/LEAST_RECENTLY_CHANGED_FIRST options."""
        new_person, modified_in_2005, modified_in_2006 = (
            self.createPersonWithTwoBranches())

        # XXX 2007-10-22 MichaelHudson: Currently we (ab)use last_scanned as
        # the date the branch was last changed.  1.1.11 will introduce a
        # date_last_modified column, which this test will need to set instead.
        modified_in_2005.last_scanned = self.xmas(2005)
        modified_in_2006.last_scanned = self.xmas(2006)

        syncUpdate(modified_in_2005)
        syncUpdate(modified_in_2006)

        getBranchesForPerson = getUtility(IBranchSet).getBranchesForPerson
        self.assertEqualByID(
            getBranchesForPerson(
                new_person,
                sort_by=BranchListingSort.MOST_RECENTLY_CHANGED_FIRST),
            [modified_in_2006, modified_in_2005])
        self.assertEqualByID(
            getBranchesForPerson(
                new_person,
                sort_by=BranchListingSort.LEAST_RECENTLY_CHANGED_FIRST),
            [modified_in_2005, modified_in_2006])

    def test_sortByAge(self):
        """Test the NEWEST_FIRST and OLDEST_FIRST options."""
        new_person, created_in_2005, created_in_2006 = (
            self.createPersonWithTwoBranches())

        # In the normal course of things date_created is not writable and so
        # we have to use removeSecurityProxy() here.
        removeSecurityProxy(created_in_2005).date_created = self.xmas(2005)
        removeSecurityProxy(created_in_2006).date_created = self.xmas(2006)

        syncUpdate(created_in_2005)
        syncUpdate(created_in_2006)

        getBranchesForPerson = getUtility(IBranchSet).getBranchesForPerson
        self.assertEqualByID(
            getBranchesForPerson(
                new_person, sort_by=BranchListingSort.NEWEST_FIRST),
            [created_in_2006, created_in_2005])
        self.assertEqualByID(
            getBranchesForPerson(
                new_person, sort_by=BranchListingSort.OLDEST_FIRST),
            [created_in_2005, created_in_2006])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
