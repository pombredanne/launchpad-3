# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Diff, etc."""

__metaclass__ = type


from unittest import TestLoader

from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer, LaunchpadZopelessLayer)
import transaction

from canonical.launchpad.database.diff import Diff, StaticDiff
from canonical.launchpad.interfaces.diff import (
    IDiff, IPreviewDiff, IStaticDiff, IStaticDiffSource)
from canonical.launchpad.testing import (
    login, login_person, TestCaseWithFactory)
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.testing import verifyObject


class TestDiff(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_providesInterface(self):
        verifyObject(IDiff, Diff())


class TestStaticDiff(TestCaseWithFactory):
    """Test that StaticDiff objects work."""

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IStaticDiff, StaticDiff())

    def test_providesSourceInterface(self):
        verifyObject(IStaticDiffSource, StaticDiff)

    def test_acquire_existing(self):
        """Ensure that acquire returns the existing StaticDiff."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.commit('First commit', rev_id='rev1')
        diff1 = StaticDiff.acquire('null:', 'rev1', tree.branch.repository)
        diff2 = StaticDiff.acquire('null:', 'rev1', tree.branch.repository)
        self.assertIs(diff1, diff2)

    def test_acquire_existing_different_repo(self):
        """The existing object is used even if the repository is different."""
        self.useBzrBranches()
        branch1, tree1 = self.create_branch_and_tree('tree1')
        tree1.commit('First commit', rev_id='rev1')
        branch2, tree2 = self.create_branch_and_tree('tree2')
        tree2.pull(tree1.branch)
        diff1 = StaticDiff.acquire('null:', 'rev1', tree1.branch.repository)
        diff2 = StaticDiff.acquire('null:', 'rev1', tree2.branch.repository)
        self.assertTrue(diff1 is diff2)

    def test_acquire_nonexisting(self):
        """A new object is created if there is no existant matching object."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.commit('First commit', rev_id='rev1')
        tree.commit('Next commit', rev_id='rev2')
        diff1 = StaticDiff.acquire('null:', 'rev1', tree.branch.repository)
        diff2 = StaticDiff.acquire('rev1', 'rev2', tree.branch.repository)
        self.assertIsNot(diff1, diff2)

    def test_acquireFromText(self):
        """acquireFromText works as expected.

        It creates a new object if there is none, but uses the existing one
        if possible.
        """
        diff_a = 'a'
        diff_b = 'b'
        static_diff = StaticDiff.acquireFromText('rev1', 'rev2', diff_a)
        self.assertEqual('rev1', static_diff.from_revision_id)
        self.assertEqual('rev2', static_diff.to_revision_id)
        static_diff2 = StaticDiff.acquireFromText('rev1', 'rev2', diff_b)
        self.assertIs(static_diff, static_diff2)

    def test_acquireFromTextEmpty(self):
        static_diff = StaticDiff.acquireFromText('rev1', 'rev2', '')
        self.assertEqual('', static_diff.diff.text)

    def test_acquireFromTextNonEmpty(self):
        static_diff = StaticDiff.acquireFromText('rev1', 'rev2', 'abc')
        transaction.commit()
        self.assertEqual('abc', static_diff.diff.text)


class TestPreviewDiff(TestCaseWithFactory):
    """Test that PreviewDiff objects work."""

    layer = LaunchpadFunctionalLayer

    def _createProposalWithPreviewDiff(self, dependent_branch=None,
                                       content='content'):
        # Create and return a preview diff.
        mp = self.factory.makeBranchMergeProposal(
            dependent_branch=dependent_branch)
        login_person(mp.registrant)
        if dependent_branch is None:
            dependent_revision_id = None
        else:
            dependent_revision_id = u'rev-c'
        mp.updatePreviewDiff(
            content, u'stat', u'rev-a', u'rev-b',
            dependent_revision_id=dependent_revision_id)
        # Make sure the librarian file is written.
        transaction.commit()
        return mp

    def test_providesInterface(self):
        # In order to test the interface provision, we need to make sure that
        # the associated diff object that is delegated to is also created.
        mp = self._createProposalWithPreviewDiff()
        verifyObject(IPreviewDiff, mp.preview_diff)

    def test_canonicalUrl(self):
        # The canonical_url of the merge diff is '+preview' after the
        # canonical_url of the merge proposal itself.
        mp = self._createProposalWithPreviewDiff()
        self.assertEqual(
            canonical_url(mp) + '/+preview-diff',
            canonical_url(mp.preview_diff))

    def test_empty_diff(self):
        # Once the source is merged into the target, the diff between the
        # branches will be empty.
        mp = self._createProposalWithPreviewDiff(content=None)
        preview = mp.preview_diff
        self.assertIs(None, preview.diff_text)
        self.assertEqual(0, preview.diff_lines_count)
        self.assertEqual(mp, preview.branch_merge_proposal)

    def test_stale_allInSync(self):
        # If the revision ids of the preview diff match the source and target
        # branches, then not stale.
        mp = self._createProposalWithPreviewDiff()
        # Log in an admin to avoid the launchpad.Edit needs for last_scanned.
        login('admin@canonical.com')
        mp.source_branch.last_scanned_id = 'rev-a'
        mp.target_branch.last_scanned_id = 'rev-b'
        self.assertEqual(False, mp.preview_diff.stale)

    def test_stale_sourceNewer(self):
        # If the source branch has a different rev id, the diff is stale.
        mp = self._createProposalWithPreviewDiff()
        # Log in an admin to avoid the launchpad.Edit needs for last_scanned.
        login('admin@canonical.com')
        mp.source_branch.last_scanned_id = 'rev-c'
        mp.target_branch.last_scanned_id = 'rev-b'
        self.assertEqual(True, mp.preview_diff.stale)

    def test_stale_targetNewer(self):
        # If the source branch has a different rev id, the diff is stale.
        mp = self._createProposalWithPreviewDiff()
        # Log in an admin to avoid the launchpad.Edit needs for last_scanned.
        login('admin@canonical.com')
        mp.source_branch.last_scanned_id = 'rev-a'
        mp.target_branch.last_scanned_id = 'rev-d'
        self.assertEqual(True, mp.preview_diff.stale)

    def test_stale_dependentBranch(self):
        # If the merge proposal has a dependent branch, then the tip revision
        # id of the dependent branch is also checked.
        dep_branch = self.factory.makeProductBranch()
        mp = self._createProposalWithPreviewDiff(dep_branch)
        # Log in an admin to avoid the launchpad.Edit needs for last_scanned.
        login('admin@canonical.com')
        mp.source_branch.last_scanned_id = 'rev-a'
        mp.target_branch.last_scanned_id = 'rev-b'
        dep_branch.last_scanned_id = 'rev-c'
        self.assertEqual(False, mp.preview_diff.stale)
        dep_branch.last_scanned_id = 'rev-d'
        self.assertEqual(True, mp.preview_diff.stale)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
