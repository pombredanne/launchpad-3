# Copyright 2007-2009 Canonical Ltd.  All rights reserved.

"""Tests for Branches."""

__metaclass__ = type

from datetime import datetime, timedelta
from unittest import TestCase, TestLoader

from pytz import UTC

from sqlobject import SQLObjectNotFound

import transaction

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad import _
from canonical.launchpad.database.branch import (
    ClearDependentBranch, ClearSeriesBranch, DeleteCodeImport,
    DeletionCallable, DeletionOperation)
from canonical.launchpad.database.branchjob import BranchDiffJob
from canonical.launchpad.database.branchmergeproposal import (
    BranchMergeProposal)
from canonical.launchpad.database.bugbranch import BugBranch
from canonical.launchpad.database.codeimport import CodeImport, CodeImportSet
from canonical.launchpad.database.codereviewcomment import CodeReviewComment
from canonical.launchpad.database.product import ProductSet
from canonical.launchpad.database.specificationbranch import (
    SpecificationBranch)
from canonical.launchpad.database.sourcepackage import SourcePackage
from canonical.launchpad.ftests import (
    login, login_person, logout, syncUpdate)
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, BranchType, CannotDeleteBranch,
    CodeReviewNotificationLevel, CreateBugParams, IBugSet,
    ILaunchpadCelebrities, IPersonSet, IProductSet, ISpecificationSet,
    InvalidBranchMergeProposal, SpecificationDefinitionStatus)
from canonical.launchpad.interfaces.branch import (
    BranchLifecycleStatus, DEFAULT_BRANCH_STATUS_IN_LISTING)
from canonical.launchpad.interfaces.branchlookup import IBranchLookup
from canonical.launchpad.interfaces.branchnamespace import IBranchNamespaceSet
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCaseWithFactory)
from canonical.launchpad.webapp.interfaces import IOpenLaunchBag

from canonical.testing import DatabaseFunctionalLayer, LaunchpadZopelessLayer


class TestCodeImport(TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        login('test@canonical.com')
        self.factory = LaunchpadObjectFactory()

    def test_branchCodeImport(self):
        """Ensure the codeImport property works correctly."""
        code_import = self.factory.makeCodeImport()
        branch = code_import.branch
        self.assertEqual(code_import, branch.code_import)
        CodeImportSet().delete(code_import)
        self.assertEqual(None, branch.code_import)


class TestBranchGetRevision(TestCaseWithFactory):
    """Make sure that `Branch.getBranchRevision` works as expected."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.branch = self.factory.makeAnyBranch()

    def _makeRevision(self, revno):
        # Make a revision and add it to the branch.
        rev = self.factory.makeRevision()
        br = self.branch.createBranchRevision(revno, rev)
        return rev

    def testGetBySequenceNumber(self):
        rev1 = self._makeRevision(1)
        branch_revision = self.branch.getBranchRevision(sequence=1)
        self.assertEqual(rev1, branch_revision.revision)
        self.assertEqual(1, branch_revision.sequence)

    def testGetByRevision(self):
        rev1 = self._makeRevision(1)
        branch_revision = self.branch.getBranchRevision(revision=rev1)
        self.assertEqual(rev1, branch_revision.revision)
        self.assertEqual(1, branch_revision.sequence)

    def testGetByRevisionId(self):
        rev1 = self._makeRevision(1)
        branch_revision = self.branch.getBranchRevision(
            revision_id=rev1.revision_id)
        self.assertEqual(rev1, branch_revision.revision)
        self.assertEqual(1, branch_revision.sequence)

    def testNonExistant(self):
        rev1 = self._makeRevision(1)
        self.assertTrue(self.branch.getBranchRevision(sequence=2) is None)
        rev2 = self.factory.makeRevision()
        self.assertTrue(self.branch.getBranchRevision(revision=rev2) is None)
        self.assertTrue(
            self.branch.getBranchRevision(revision_id='not found') is None)

    def testInvalidParams(self):
        self.assertRaises(AssertionError, self.branch.getBranchRevision)
        rev1 = self._makeRevision(1)
        self.assertRaises(AssertionError, self.branch.getBranchRevision,
                          sequence=1, revision=rev1,
                          revision_id=rev1.revision_id)
        self.assertRaises(AssertionError, self.branch.getBranchRevision,
                          sequence=1, revision=rev1)
        self.assertRaises(AssertionError, self.branch.getBranchRevision,
                          revision=rev1, revision_id=rev1.revision_id)
        self.assertRaises(AssertionError, self.branch.getBranchRevision,
                          sequence=1, revision_id=rev1.revision_id)


class TestGetMainlineBranchRevisions(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_getMainlineBranchRevisions(self):
        """Only gets the mainline revisions, ignoring the others."""
        branch = self.factory.makeBranch()
        self.factory.makeBranchRevision(branch, 'rev1', 1)
        self.factory.makeBranchRevision(branch, 'rev2', 2)
        self.factory.makeBranchRevision(branch, 'rev2b', None)
        result_set = branch.getMainlineBranchRevisions(
            ['rev1', 'rev2', 'rev3'])
        revid_set = set(
            branch_revision.revision.revision_id for
            branch_revision in result_set)
        self.assertEqual(set(['rev1', 'rev2']), revid_set)

    def test_getMainlineBranchRevisionsWrongBranch(self):
        """Only gets the revisions for this branch, ignoring the others."""
        branch = self.factory.makeBranch()
        other_branch = self.factory.makeBranch()
        self.factory.makeBranchRevision(branch, 'rev1', 1)
        self.factory.makeBranchRevision(other_branch, 'rev1b', 2)
        result_set = branch.getMainlineBranchRevisions(
            ['rev1', 'rev1b'])
        revid_set = set(
            branch_revision.revision.revision_id for
            branch_revision in result_set)
        self.assertEqual(set(['rev1']), revid_set)


class TestBranch(TestCaseWithFactory):
    """Test basic properties about Launchpad database branches."""

    layer = DatabaseFunctionalLayer

    def test_pullURLHosted(self):
        # Hosted branches are pulled from internal Launchpad URLs.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)
        self.assertEqual(
            'lp-hosted:///%s' % branch.unique_name, branch.getPullURL())

    def test_pullURLMirrored(self):
        # Mirrored branches are pulled from their actual URLs -- that's the
        # point.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.MIRRORED)
        self.assertEqual(branch.url, branch.getPullURL())

    def test_pullURLImported(self):
        # Imported branches are pulled from the import servers at locations
        # corresponding to the hex id of the branch being mirrored.
        import_server = config.launchpad.bzr_imports_root_url
        branch = self.factory.makeAnyBranch(branch_type=BranchType.IMPORTED)
        self.assertEqual(
            '%s/%08x' % (import_server, branch.id), branch.getPullURL())

    def test_pullURLRemote(self):
        # We cannot mirror remote branches. getPullURL raises an
        # AssertionError.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.REMOTE)
        self.assertRaises(AssertionError, branch.getPullURL)

    def test_unique_name_product(self):
        branch = self.factory.makeProductBranch()
        self.assertEqual(
            '~%s/%s/%s' % (
                branch.owner.name, branch.product.name, branch.name),
            branch.unique_name)

    def test_unique_name_junk(self):
        branch = self.factory.makePersonalBranch()
        self.assertEqual(
            '~%s/+junk/%s' % (branch.owner.name, branch.name),
            branch.unique_name)

    def test_unique_name_source_package(self):
        branch = self.factory.makePackageBranch()
        self.assertEqual(
            '~%s/%s/%s/%s/%s' % (
                branch.owner.name, branch.distribution.name,
                branch.distroseries.name, branch.sourcepackagename.name,
                branch.name),
            branch.unique_name)

    def test_target_name_junk(self):
        branch = self.factory.makePersonalBranch()
        self.assertEqual('+junk', branch.target.name)

    def test_target_name_product(self):
        branch = self.factory.makeProductBranch()
        self.assertEqual(branch.product.name, branch.target.name)

    def test_target_name_package(self):
        branch = self.factory.makePackageBranch()
        self.assertEqual(
            '%s/%s/%s' % (
                branch.distribution.name, branch.distroseries.name,
                branch.sourcepackagename.name),
            branch.target.name)

    def makeLaunchBag(self):
        return getUtility(IOpenLaunchBag)

    def test_addToLaunchBag_product(self):
        # Branches are not added directly to the launchbag. Instead,
        # information about their target is added.
        branch = self.factory.makeProductBranch()
        launchbag = self.makeLaunchBag()
        branch.addToLaunchBag(launchbag)
        self.assertEqual(branch.product, launchbag.product)

    def test_addToLaunchBag_personal(self):
        # Junk branches may also be added to the launchbag.
        branch = self.factory.makePersonalBranch()
        launchbag = self.makeLaunchBag()
        branch.addToLaunchBag(launchbag)
        self.assertIs(None, launchbag.product)

    def test_addToLaunchBag_package(self):
        # Package branches can be added to the launchbag.
        branch = self.factory.makePackageBranch()
        launchbag = self.makeLaunchBag()
        branch.addToLaunchBag(launchbag)
        self.assertEqual(branch.distroseries, launchbag.distroseries)
        self.assertEqual(branch.distribution, launchbag.distribution)
        self.assertEqual(branch.sourcepackage, launchbag.sourcepackage)
        self.assertIs(None, branch.product)

    def test_distribution_personal(self):
        # The distribution property of a branch is None for personal branches.
        branch = self.factory.makePersonalBranch()
        self.assertIs(None, branch.distribution)

    def test_distribution_product(self):
        # The distribution property of a branch is None for product branches.
        branch = self.factory.makeProductBranch()
        self.assertIs(None, branch.distribution)

    def test_distribution_package(self):
        # The distribution property of a branch is the distribution of the
        # distroseries for package branches.
        branch = self.factory.makePackageBranch()
        self.assertEqual(
            branch.distroseries.distribution, branch.distribution)

    def test_sourcepackage_personal(self):
        # The sourcepackage property of a branch is None for personal
        # branches.
        branch = self.factory.makePersonalBranch()
        self.assertIs(None, branch.sourcepackage)

    def test_sourcepackage_product(self):
        # The sourcepackage property of a branch is None for product branches.
        branch = self.factory.makeProductBranch()
        self.assertIs(None, branch.sourcepackage)

    def test_sourcepackage_package(self):
        # The sourcepackage property of a branch is the ISourcePackage built
        # from the distroseries and sourcepackagename of the branch.
        branch = self.factory.makePackageBranch()
        self.assertEqual(
            SourcePackage(branch.sourcepackagename, branch.distroseries),
            branch.sourcepackage)


class TestBranchDeletion(TestCaseWithFactory):
    """Test the different cases that makes a branch deletable or not."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'test@canonical.com')
        self.product = ProductSet().getByName('firefox')
        self.user = getUtility(IPersonSet).getByEmail('test@canonical.com')
        self.branch = self.factory.makeProductBranch(
            name='to-delete', owner=self.user, product=self.product)
        # The owner of the branch is subscribed to the branch when it is
        # created.  The tests here assume no initial connections, so
        # unsubscribe the branch owner here.
        self.branch.unsubscribe(self.branch.owner)

    def tearDown(self):
        logout()

    def test_deletable(self):
        """A newly created branch can be deleted without any problems."""
        self.assertEqual(self.branch.canBeDeleted(), True,
                         "A newly created branch should be able to be "
                         "deleted.")
        branch_id = self.branch.id
        branch_set = getUtility(IBranchLookup)
        self.branch.destroySelf()
        self.assert_(branch_set.get(branch_id) is None,
                     "The branch has not been deleted.")

    def test_stackedBranchDisablesDeletion(self):
        # A branch that is stacked upon cannot be deleted.
        branch = self.factory.makeAnyBranch(stacked_on=self.branch)
        self.assertFalse(self.branch.canBeDeleted())

    def test_subscriptionDoesntDisableDeletion(self):
        """A branch that has a subscription can be deleted."""
        self.branch.subscribe(
            self.user, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.NOEMAIL)
        self.assertEqual(True, self.branch.canBeDeleted())

    def test_codeImportDisablesDeletion(self):
        """A branch that has an attached code import can't be deleted."""
        code_import = LaunchpadObjectFactory().makeCodeImport()
        branch = code_import.branch
        self.assertEqual(branch.canBeDeleted(), False,
                         "A branch that has a import is not deletable.")
        self.assertRaises(CannotDeleteBranch, branch.destroySelf)

    def test_bugBranchLinkDisablesDeletion(self):
        """A branch linked to a bug cannot be deleted."""
        params = CreateBugParams(
            owner=self.user, title='Firefox bug', comment='blah')
        params.setBugTarget(product=self.product)
        bug = getUtility(IBugSet).createBug(params)
        bug.addBranch(self.branch, self.user)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch linked to a bug is not deletable.")
        self.assertRaises(CannotDeleteBranch, self.branch.destroySelf)

    def test_specBranchLinkDisablesDeletion(self):
        """A branch linked to a spec cannot be deleted."""
        spec = getUtility(ISpecificationSet).new(
            name='some-spec', title='Some spec', product=self.product,
            owner=self.user, summary='', specurl=None,
            definition_status=SpecificationDefinitionStatus.NEW)
        spec.linkBranch(self.branch, self.user)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch linked to a spec is not deletable.")
        self.assertRaises(CannotDeleteBranch, self.branch.destroySelf)

    def test_associatedProductSeriesBranchDisablesDeletion(self):
        """A branch linked as a branch to a product series cannot be
        deleted.
        """
        self.product.development_focus.branch = self.branch
        syncUpdate(self.product.development_focus)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch that is a user branch for a product series"
                         " is not deletable.")
        self.assertRaises(CannotDeleteBranch, self.branch.destroySelf)

    def test_revisionsDeletable(self):
        """A branch that has some revisions can be deleted."""
        revision = self.factory.makeRevision()
        self.branch.createBranchRevision(0, revision)
        # Need to commit the addition to make sure that the branch revisions
        # are recorded as there and that the appropriate deferred foreign keys
        # are set up.
        transaction.commit()
        self.assertEqual(self.branch.canBeDeleted(), True,
                         "A branch that has a revision is deletable.")
        unique_name = self.branch.unique_name
        self.branch.destroySelf()
        # Commit again to trigger the deferred indices.
        transaction.commit()
        branch_lookup = getUtility(IBranchLookup)
        self.assertEqual(branch_lookup.getByUniqueName(unique_name), None,
                         "Branch was not deleted.")

    def test_landingTargetDisablesDeletion(self):
        """A branch with a landing target cannot be deleted."""
        target_branch = self.factory.makeProductBranch(
            name='landing-target', owner=self.user, product=self.product)
        self.branch.addLandingTarget(self.user, target_branch)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch with a landing target is not deletable.")
        self.assertRaises(CannotDeleteBranch, self.branch.destroySelf)

    def test_landingCandidateDisablesDeletion(self):
        """A branch with a landing candidate cannot be deleted."""
        source_branch = self.factory.makeProductBranch(
            name='landing-candidate', owner=self.user, product=self.product)
        source_branch.addLandingTarget(self.user, self.branch)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch with a landing candidate is not"
                         " deletable.")
        self.assertRaises(CannotDeleteBranch, self.branch.destroySelf)

    def test_dependentBranchDisablesDeletion(self):
        """A branch that is a dependent branch cannot be deleted."""
        source_branch = self.factory.makeProductBranch(
            name='landing-candidate', owner=self.user, product=self.product)
        target_branch = self.factory.makeProductBranch(
            name='landing-target', owner=self.user, product=self.product)
        source_branch.addLandingTarget(self.user, target_branch, self.branch)
        self.assertEqual(self.branch.canBeDeleted(), False,
                         "A branch with a dependent target is not deletable.")
        self.assertRaises(CannotDeleteBranch, self.branch.destroySelf)

    def test_relatedBranchJobsDeleted(self):
        # A branch with an associated branch job will delete those jobs.
        branch = self.factory.makeAnyBranch()
        BranchDiffJob.create(branch, 'from-spec', 'to-spec')
        branch.destroySelf()
        # Need to commit the transaction to fire off the constraint checks.
        transaction.commit()


class TestBranchDeletionConsequences(TestCase):
    """Test determination and application of branch deletion consequences."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        login('test@canonical.com')
        self.factory = LaunchpadObjectFactory()
        # Has to be a product branch because of merge proposals.
        self.branch = self.factory.makeProductBranch()
        # The owner of the branch is subscribed to the branch when it is
        # created.  The tests here assume no initial connections, so
        # unsubscribe the branch owner here.
        self.branch.unsubscribe(self.branch.owner)

    def test_plainBranch(self):
        """Ensure that a fresh branch has no deletion requirements."""
        self.assertEqual({}, self.branch.deletionRequirements())

    def makeMergeProposals(self):
        """Produce a merge proposal for testing purposes."""
        target_branch = self.factory.makeProductBranch(
            product=self.branch.product)
        dependent_branch = self.factory.makeProductBranch(
            product=self.branch.product)
        # Remove the implicit subscriptions.
        target_branch.unsubscribe(target_branch.owner)
        dependent_branch.unsubscribe(dependent_branch.owner)
        merge_proposal1 = self.branch.addLandingTarget(
            self.branch.owner, target_branch, dependent_branch)
        # Disable this merge proposal, to allow creating a new identical one
        lp_admins = getUtility(ILaunchpadCelebrities).admin
        merge_proposal1.rejectBranch(lp_admins, 'null:')
        syncUpdate(merge_proposal1)
        merge_proposal2 = self.branch.addLandingTarget(
            self.branch.owner, target_branch, dependent_branch)
        return merge_proposal1, merge_proposal2

    def test_branchWithMergeProposal(self):
        """Ensure that deletion requirements with a merge proposal are right.

        Each branch related to the merge proposal is tested to ensure it
        produces a unique, correct result.
        """
        merge_proposal1, merge_proposal2 = self.makeMergeProposals()
        self.assertEqual({
            merge_proposal1:
            ('delete', _('This branch is the source branch of this merge'
             ' proposal.')),
            merge_proposal2:
            ('delete', _('This branch is the source branch of this merge'
             ' proposal.'))
             },
                         self.branch.deletionRequirements())
        self.assertEqual({
            merge_proposal1:
            ('delete', _('This branch is the target branch of this merge'
             ' proposal.')),
            merge_proposal2:
            ('delete', _('This branch is the target branch of this merge'
             ' proposal.'))
            },
            merge_proposal1.target_branch.deletionRequirements())
        self.assertEqual({
            merge_proposal1:
            ('alter', _('This branch is the dependent branch of this merge'
             ' proposal.')),
            merge_proposal2:
            ('alter', _('This branch is the dependent branch of this merge'
             ' proposal.'))
            },
            merge_proposal1.dependent_branch.deletionRequirements())

    def test_deleteMergeProposalSource(self):
        """Merge proposal source branches can be deleted with break_links."""
        merge_proposal1, merge_proposal2 = self.makeMergeProposals()
        merge_proposal1_id = merge_proposal1.id
        BranchMergeProposal.get(merge_proposal1_id)
        self.branch.destroySelf(break_references=True)
        self.assertRaises(SQLObjectNotFound,
            BranchMergeProposal.get, merge_proposal1_id)

    def test_deleteMergeProposalTarget(self):
        """Merge proposal target branches can be deleted with break_links."""
        merge_proposal1, merge_proposal2 = self.makeMergeProposals()
        merge_proposal1_id = merge_proposal1.id
        BranchMergeProposal.get(merge_proposal1_id)
        merge_proposal1.target_branch.destroySelf(break_references=True)
        self.assertRaises(SQLObjectNotFound,
            BranchMergeProposal.get, merge_proposal1_id)

    def test_deleteMergeProposalDependent(self):
        """break_links enables deleting merge proposal dependant branches."""
        merge_proposal1, merge_proposal2 = self.makeMergeProposals()
        merge_proposal1_id = merge_proposal1.id
        merge_proposal1.dependent_branch.destroySelf(break_references=True)
        self.assertEqual(None, merge_proposal1.dependent_branch)

    def test_deleteSourceCodeReviewComment(self):
        """Deletion of branches that have CodeReviewComments works."""
        comment = self.factory.makeCodeReviewComment()
        comment_id = comment.id
        branch = comment.branch_merge_proposal.source_branch
        branch.destroySelf(break_references=True)
        self.assertRaises(
            SQLObjectNotFound, CodeReviewComment.get, comment_id)

    def test_deleteTargetCodeReviewComment(self):
        """Deletion of branches that have CodeReviewComments works."""
        comment = self.factory.makeCodeReviewComment()
        comment_id = comment.id
        branch = comment.branch_merge_proposal.target_branch
        branch.destroySelf(break_references=True)
        self.assertRaises(
            SQLObjectNotFound, CodeReviewComment.get, comment_id)

    def test_branchWithBugRequirements(self):
        """Deletion requirements for a branch with a bug are right."""
        bug = self.factory.makeBug()
        bug.addBranch(self.branch, self.branch.owner)
        self.assertEqual({bug.bug_branches[0]:
            ('delete', _('This bug is linked to this branch.'))},
            self.branch.deletionRequirements())

    def test_branchWithBugDeletion(self):
        """break_links allows deleting a branch with a bug."""
        bug1 = self.factory.makeBug()
        bug2 = self.factory.makeBug()
        bug1.addBranch(self.branch, self.branch.owner)
        bug_branch1 = bug1.bug_branches[0]
        bug_branch1_id = bug_branch1.id
        self.branch.destroySelf(break_references=True)
        self.assertRaises(SQLObjectNotFound, BugBranch.get, bug_branch1_id)

    def test_branchWithSpecRequirements(self):
        """Deletion requirements for a branch with a spec are right."""
        spec = self.factory.makeSpecification()
        spec.linkBranch(self.branch, self.branch.owner)
        self.assertEqual({self.branch.spec_links[0]:
            ('delete', _(
                'This blueprint is linked to this branch.'))},
             self.branch.deletionRequirements())

    def test_branchWithSpecDeletion(self):
        """break_links allows deleting a branch with a spec."""
        spec1 = self.factory.makeSpecification()
        spec1.linkBranch(self.branch, self.branch.owner)
        spec1_branch_id = self.branch.spec_links[0].id
        spec2 = self.factory.makeSpecification()
        spec2.linkBranch(self.branch, self.branch.owner)
        spec2_branch_id = self.branch.spec_links[1].id
        self.branch.destroySelf(break_references=True)
        self.assertRaises(SQLObjectNotFound, SpecificationBranch.get,
                          spec1_branch_id)
        self.assertRaises(SQLObjectNotFound, SpecificationBranch.get,
                          spec2_branch_id)

    def test_branchWithSeriesRequirements(self):
        """Deletion requirements for a series' branch are right."""
        series = self.factory.makeSeries(branch=self.branch)
        self.assertEqual(
            {series: ('alter',
            _('This series is linked to this branch.'))},
            self.branch.deletionRequirements())

    def test_branchWithSeriesDeletion(self):
        """break_links allows deleting a series' branch."""
        series1 = self.factory.makeSeries(branch=self.branch)
        series2 = self.factory.makeSeries(branch=self.branch)
        self.branch.destroySelf(break_references=True)
        self.assertEqual(None, series1.branch)
        self.assertEqual(None, series2.branch)

    def test_branchWithCodeImportRequirements(self):
        """Deletion requirements for a code import branch are right"""
        code_import = self.factory.makeCodeImport()
        # Remove the implicit branch subscription first.
        code_import.branch.unsubscribe(code_import.branch.owner)
        self.assertEqual({code_import:
            ('delete', _('This is the import data for this branch.'))},
             code_import.branch.deletionRequirements())

    def test_branchWithCodeImportDeletion(self):
        """break_links allows deleting a code import branch."""
        code_import = self.factory.makeCodeImport()
        code_import_id = code_import.id
        self.factory.makeCodeImportJob(code_import)
        code_import.branch.destroySelf(break_references=True)
        self.assertRaises(
            SQLObjectNotFound, CodeImport.get, code_import_id)

    def test_sourceBranchWithCodeReviewVoteReference(self):
        """Break_references handles CodeReviewVoteReference source branch."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        merge_proposal.nominateReviewer(self.factory.makePerson(),
                                        self.factory.makePerson())
        merge_proposal.source_branch.destroySelf(break_references=True)

    def test_targetBranchWithCodeReviewVoteReference(self):
        """Break_references handles CodeReviewVoteReference target branch."""
        merge_proposal = self.factory.makeBranchMergeProposal()
        merge_proposal.nominateReviewer(self.factory.makePerson(),
                                        self.factory.makePerson())
        merge_proposal.target_branch.destroySelf(break_references=True)

    def test_ClearDependentBranch(self):
        """ClearDependent.__call__ must clear the dependent branch."""
        merge_proposal = removeSecurityProxy(self.makeMergeProposals()[0])
        ClearDependentBranch(merge_proposal)()
        self.assertEqual(None, merge_proposal.dependent_branch)

    def test_ClearSeriesBranch(self):
        """ClearSeriesBranch.__call__ must clear the user branch."""
        series = removeSecurityProxy(self.factory.makeSeries(
            branch=self.branch))
        ClearSeriesBranch(series, self.branch)()
        self.assertEqual(None, series.branch)

    def test_DeletionOperation(self):
        """DeletionOperation.__call__ is not implemented."""
        self.assertRaises(NotImplementedError, DeletionOperation('a', 'b'))

    def test_DeletionCallable(self):
        """DeletionCallable must invoke the callable."""
        spec = self.factory.makeSpecification()
        spec_link = spec.linkBranch(self.branch, self.branch.owner)
        spec_link_id = spec_link.id
        DeletionCallable(spec, 'blah', spec_link.destroySelf)()
        self.assertRaises(SQLObjectNotFound, SpecificationBranch.get,
                          spec_link_id)

    def test_DeleteCodeImport(self):
        """DeleteCodeImport.__call__ must delete the CodeImport."""
        code_import = self.factory.makeCodeImport()
        code_import_id = code_import.id
        self.factory.makeCodeImportJob(code_import)
        DeleteCodeImport(code_import)()
        self.assertRaises(
            SQLObjectNotFound, CodeImport.get, code_import_id)


class StackedBranches(TestCaseWithFactory):
    """Tests for showing branches stacked on another."""

    layer = DatabaseFunctionalLayer

    def testNoBranchesStacked(self):
        # getStackedBranches returns an empty collection if there are no
        # branches stacked on it.
        branch = self.factory.makeAnyBranch()
        self.assertEqual(set(), set(branch.getStackedBranches()))

    def testSingleBranchStacked(self):
        # some_branch.getStackedBranches returns a collection of branches
        # stacked on some_branch.
        branch = self.factory.makeAnyBranch()
        stacked_branch = self.factory.makeAnyBranch(stacked_on=branch)
        self.assertEqual(
            set([stacked_branch]), set(branch.getStackedBranches()))

    def testMultipleBranchesStacked(self):
        # some_branch.getStackedBranches returns a collection of branches
        # stacked on some_branch.
        branch = self.factory.makeAnyBranch()
        stacked_a = self.factory.makeAnyBranch(stacked_on=branch)
        stacked_b = self.factory.makeAnyBranch(stacked_on=branch)
        self.assertEqual(
            set([stacked_a, stacked_b]), set(branch.getStackedBranches()))

    def testStackedBranchesIncompleteMirrorsNoBranches(self):
        # some_branch.getStackedBranchesWithIncompleteMirrors does not include
        # stacked branches that haven't been mirrored at all.
        branch = self.factory.makeAnyBranch()
        stacked_a = self.factory.makeAnyBranch(stacked_on=branch)
        self.assertEqual(
            set(), set(branch.getStackedBranchesWithIncompleteMirrors()))

    def testStackedBranchesIncompleteMirrors(self):
        # some_branch.getStackedBranchesWithIncompleteMirrors returns branches
        # stacked on some_branch that had their mirrors started but not
        # finished.
        branch = self.factory.makeAnyBranch()
        stacked_a = self.factory.makeAnyBranch(stacked_on=branch)
        stacked_a.startMirroring()
        self.assertEqual(
            set([stacked_a]),
            set(branch.getStackedBranchesWithIncompleteMirrors()))

    def testStackedBranchesIncompleteMirrorsNotStacked(self):
        # some_branch.getStackedBranchesWithIncompleteMirrors does not include
        # branches with incomplete mirrors that are not stacked on
        # some_branch.
        branch = self.factory.makeAnyBranch()
        not_stacked = self.factory.makeAnyBranch()
        not_stacked.startMirroring()
        self.assertEqual(
            set(), set(branch.getStackedBranchesWithIncompleteMirrors()))

    def testStackedBranchesCompleteMirrors(self):
        # some_branch.getStackedBranchesWithIncompleteMirrors does not include
        # branches that have been successfully mirrored.
        branch = self.factory.makeAnyBranch()
        stacked_a = self.factory.makeAnyBranch(stacked_on=branch)
        stacked_a.startMirroring()
        stacked_a.mirrorComplete(self.factory.getUniqueString())
        self.assertEqual(
            set(), set(branch.getStackedBranchesWithIncompleteMirrors()))

    def testStackedBranchesFailedMirrors(self):
        # some_branch.getStackedBranchesWithIncompleteMirrors includes
        # branches that failed to mirror. This is not directly desired, but is
        # a consequence of wanting to include branches that have started,
        # failed, then started again.
        branch = self.factory.makeAnyBranch()
        stacked_a = self.factory.makeAnyBranch(stacked_on=branch)
        stacked_a.startMirroring()
        stacked_a.mirrorFailed(self.factory.getUniqueString())
        self.assertEqual(
            set([stacked_a]),
            set(branch.getStackedBranchesWithIncompleteMirrors()))

    def testStackedBranchesFailedThenStartedMirrors(self):
        # some_branch.getStackedBranchesWithIncompleteMirrors includes
        # branches that had a failed mirror but have since been started.
        branch = self.factory.makeAnyBranch()
        stacked_a = self.factory.makeAnyBranch(stacked_on=branch)
        stacked_a.startMirroring()
        stacked_a.mirrorFailed(self.factory.getUniqueString())
        stacked_a.startMirroring()
        self.assertEqual(
            set([stacked_a]),
            set(branch.getStackedBranchesWithIncompleteMirrors()))

    def testStackedBranchesMirrorRequested(self):
        # some_branch.getStackedBranchesWithIncompleteMirrors does not include
        # branches that have only had a mirror requested.
        branch = self.factory.makeAnyBranch()
        stacked_a = self.factory.makeAnyBranch(stacked_on=branch)
        stacked_a.requestMirror()
        self.assertEqual(
            set(), set(branch.getStackedBranchesWithIncompleteMirrors()))


class BranchAddLandingTarget(TestCaseWithFactory):
    """Exercise all the code paths for adding a landing target."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        self.product = getUtility(IProductSet).getByName('firefox')

        self.user = getUtility(IPersonSet).getByName('no-priv')
        self.source = self.factory.makeProductBranch(
            name='source-branch', owner=self.user, product=self.product)
        self.target = self.factory.makeProductBranch(
            name='target-branch', owner=self.user, product=self.product)
        self.dependent = self.factory.makeProductBranch(
            name='dependent-branch', owner=self.user, product=self.product)

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

    def test_existingRejectedMergeProposal(self):
        """If there is an existing rejected merge proposal for the source and
        target branch pair, then another landing target specifying the same
        pair is fine.
        """
        proposal = self.source.addLandingTarget(
            self.user, self.target, self.dependent)
        proposal.rejectBranch(self.user, 'some_revision')
        syncUpdate(proposal)
        new_proposal = self.source.addLandingTarget(
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


class BranchDateLastModified(TestCaseWithFactory):
    """Exercies the situations where date_last_modifed is udpated."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self, 'test@canonical.com')

    def test_initialValue(self):
        """Initially the date_last_modifed is the date_created."""
        branch = self.factory.makeAnyBranch()
        self.assertEqual(branch.date_last_modified, branch.date_created)

    def test_bugBranchLinkUpdates(self):
        """Linking a branch to a bug updates the last modified time."""
        date_created = datetime(2000, 1, 1, 12, tzinfo=UTC)
        branch = self.factory.makeAnyBranch(date_created=date_created)
        self.assertEqual(branch.date_last_modified, date_created)

        params = CreateBugParams(
            owner=branch.owner, title='A bug', comment='blah')
        params.setBugTarget(product=branch.product)
        bug = getUtility(IBugSet).createBug(params)

        bug.addBranch(branch, branch.owner)
        self.assertTrue(branch.date_last_modified > date_created,
                        "Date last modified was not updated.")

    def test_updateScannedDetails_with_null_revision(self):
        # If updateScannedDetails is called with a null revision, it
        # effectively means that there is an empty branch, so we can't use the
        # revision date, so we set the last modified time to UTC_NOW.
        date_created = datetime(2000, 1, 1, 12, tzinfo=UTC)
        branch = self.factory.makeAnyBranch(date_created=date_created)
        branch.updateScannedDetails(None, 0)
        self.assertSqlAttributeEqualsDate(
            branch, 'date_last_modified', UTC_NOW)

    def test_updateScannedDetails_with_revision(self):
        # If updateScannedDetails is called with a revision with which has a
        # revision date set in the past (the usual case), the last modified
        # time of the branch is set to be the date from the Bazaar revision
        # (Revision.revision_date).
        date_created = datetime(2000, 1, 1, 12, tzinfo=UTC)
        branch = self.factory.makeAnyBranch(date_created=date_created)
        revision_date = datetime(2005, 2, 2, 12, tzinfo=UTC)
        revision = self.factory.makeRevision(revision_date=revision_date)
        branch.updateScannedDetails(revision, 1)
        self.assertEqual(revision_date, branch.date_last_modified)

    def test_updateScannedDetails_with_future_revision(self):
        # If updateScannedDetails is called with a revision with which has a
        # revision date set in the future, UTC_NOW is used as the last modifed
        # time.  date_created = datetime(2000, 1, 1, 12, tzinfo=UTC)
        date_created = datetime(2000, 1, 1, 12, tzinfo=UTC)
        branch = self.factory.makeAnyBranch(date_created=date_created)
        revision_date = datetime.now(UTC) + timedelta(days=1000)
        revision = self.factory.makeRevision(revision_date=revision_date)
        branch.updateScannedDetails(revision, 1)
        self.assertSqlAttributeEqualsDate(
            branch, 'date_last_modified', UTC_NOW)


class TestBranchLifecycleStatus(TestCaseWithFactory):
    """Exercises changes in lifecycle status."""
    layer = DatabaseFunctionalLayer

    def checkStatusAfterUpdate(self, initial_state, expected_state):
        # Make sure that the lifecycle status of the branch with the initial
        # lifecycle state to be the expected_state after a revision has been
        # scanned.
        branch = self.factory.makeAnyBranch(lifecycle_status=initial_state)
        revision = self.factory.makeRevision()
        branch.updateScannedDetails(revision, 1)
        self.assertEqual(expected_state, branch.lifecycle_status)

    def test_updateScannedDetails_active_branch(self):
        # If a new revision is scanned, and the branch is in an active state,
        # then the lifecycle status isn't changed.
        for state in DEFAULT_BRANCH_STATUS_IN_LISTING:
            self.checkStatusAfterUpdate(state, state)

    def test_updateScannedDetails_inactive_branch(self):
        # If a branch is inactive (merged or abandonded) and a new revision is
        # scanned, the branch is moved to the development state.
        for state in (BranchLifecycleStatus.MERGED,
                      BranchLifecycleStatus.ABANDONED):
            self.checkStatusAfterUpdate(
                state, BranchLifecycleStatus.DEVELOPMENT)


class TestCreateBranchRevisionFromIDs(TestCaseWithFactory):
    """Tests for `Branch.createBranchRevisionFromIDs`."""

    layer = DatabaseFunctionalLayer

    def test_simple(self):
        # createBranchRevisionFromIDs when passed a single revid, sequence
        # pair, creates the appropriate BranchRevision object.
        branch = self.factory.makeAnyBranch()
        rev = self.factory.makeRevision()
        revision_number = self.factory.getUniqueInteger()
        branch.createBranchRevisionFromIDs(
            [(rev.revision_id, revision_number)])
        branch_revision = branch.getBranchRevision(revision=rev)
        self.assertEqual(revision_number, branch_revision.sequence)

    def test_multiple(self):
        # createBranchRevisionFromIDs when passed multiple revid, sequence
        # pairs, creates the appropriate BranchRevision objects.
        branch = self.factory.makeAnyBranch()
        revision_to_number = {}
        revision_id_sequence_pairs = []
        for i in range(10):
            rev = self.factory.makeRevision()
            revision_number = self.factory.getUniqueInteger()
            revision_to_number[rev] = revision_number
            revision_id_sequence_pairs.append(
                (rev.revision_id, revision_number))
        branch.createBranchRevisionFromIDs(revision_id_sequence_pairs)
        for rev in revision_to_number:
            branch_revision = branch.getBranchRevision(revision=rev)
            self.assertEqual(
                revision_to_number[rev], branch_revision.sequence)

    def test_empty(self):
        # createBranchRevisionFromIDs does not fail when passed no pairs.
        branch = self.factory.makeAnyBranch()
        branch.createBranchRevisionFromIDs([])

    def test_call_twice_in_one_transaction(self):
        # createBranchRevisionFromIDs creates temporary tables, but cleans
        # after itself so that it can safely be called twice in one
        # transaction.
        branch = self.factory.makeAnyBranch()
        rev = self.factory.makeRevision()
        revision_number = self.factory.getUniqueInteger()
        branch.createBranchRevisionFromIDs(
            [(rev.revision_id, revision_number)])
        rev = self.factory.makeRevision()
        revision_number = self.factory.getUniqueInteger()
        # This is just "assertNotRaises"
        branch.createBranchRevisionFromIDs(
            [(rev.revision_id, revision_number)])


class TestCodebrowseURL(TestCaseWithFactory):
    """Tests for `Branch.codebrowse_url`."""

    layer = DatabaseFunctionalLayer

    def test_simple(self):
        # The basic codebrowse URL for a public branch is a 'http' url.
        branch = self.factory.makeAnyBranch()
        self.assertEqual(
            'http://bazaar.launchpad.dev/' + branch.unique_name,
            branch.codebrowse_url())

    def test_private(self):
        # The codebrowse URL for a private branch is a 'https' url.
        owner = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(private=True, owner=owner)
        login_person(owner)
        self.assertEqual(
            'https://bazaar.launchpad.dev/' + branch.unique_name,
            branch.codebrowse_url())

    def test_extra_args(self):
        # Any arguments to codebrowse_url are appended to the URL.
        branch = self.factory.makeAnyBranch()
        self.assertEqual(
            'http://bazaar.launchpad.dev/' + branch.unique_name + '/a/b',
            branch.codebrowse_url('a', 'b'))


class TestBranchNamespace(TestCaseWithFactory):
    """Tests for `IBranch.namespace`."""

    layer = DatabaseFunctionalLayer

    def assertNamespaceEqual(self, namespace_one, namespace_two):
        """Assert that `namespace_one` equals `namespace_two`."""
        namespace_one = removeSecurityProxy(namespace_one)
        namespace_two = removeSecurityProxy(namespace_two)
        self.assertEqual(namespace_one.__class__, namespace_two.__class__)
        self.assertEqual(namespace_one.owner, namespace_two.owner)
        self.assertEqual(
            getattr(namespace_one, 'sourcepackage', None),
            getattr(namespace_two, 'sourcepackage', None))
        self.assertEqual(
            getattr(namespace_one, 'product', None),
            getattr(namespace_two, 'product', None))

    def test_namespace_personal(self):
        # The namespace attribute of a personal branch points to the namespace
        # that corresponds to ~owner/+junk.
        branch = self.factory.makePersonalBranch()
        namespace = getUtility(IBranchNamespaceSet).get(person=branch.owner)
        self.assertNamespaceEqual(namespace, branch.namespace)

    def test_namespace_package(self):
        # The namespace attribute of a package branch points to the namespace
        # that corresponds to
        # ~owner/distribution/distroseries/sourcepackagename.
        branch = self.factory.makePackageBranch()
        namespace = getUtility(IBranchNamespaceSet).get(
            person=branch.owner, distroseries=branch.distroseries,
            sourcepackagename=branch.sourcepackagename)
        self.assertNamespaceEqual(namespace, branch.namespace)

    def test_namespace_product(self):
        # The namespace attribute of a product branch points to the namespace
        # that corresponds to ~owner/product.
        branch = self.factory.makeProductBranch()
        namespace = getUtility(IBranchNamespaceSet).get(
            person=branch.owner, product=branch.product)
        self.assertNamespaceEqual(namespace, branch.namespace)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
