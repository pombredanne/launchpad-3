# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Diff, etc."""

__metaclass__ = type


from unittest import TestLoader

from bzrlib.bzrdir import BzrDir
from bzrlib.transport import get_transport
from canonical.testing import LaunchpadZopelessLayer, DatabaseFunctionalLayer
from sqlobject import SQLObjectNotFound
import transaction

from canonical.codehosting.scanner.tests.test_bzrsync import (
    FakeTransportServer)
from canonical.launchpad.database.diff import Diff, StaticDiff, StaticDiffJob
from canonical.launchpad.interfaces.diff import (
    IDiff, IStaticDiff, IStaticDiffSource, IStaticDiffJob)
from canonical.launchpad.database.job import Job
from canonical.launchpad.interfaces.job import JobStatus
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.testing import verifyObject


class TestDiff(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_providesInterface(self):
        verifyObject(IDiff, Diff())


class BzrTestCase(TestCaseWithFactory):
    """Test case providing access to a fake branch location."""

    def create_branch_and_tree(self, tree_location='.'):
        """Create a database branch, bzr branch and bzr checkout."

        :return: a `Branch` and a workingtree.
        """
        db_branch = self.factory.makeBranch()
        transport = get_transport(db_branch.warehouse_url)
        transport.clone('../..').ensure_base()
        transport.clone('..').ensure_base()
        bzr_branch = BzrDir.create_branch_convenience(db_branch.warehouse_url)
        return db_branch, bzr_branch.create_checkout(tree_location)

    def useBzrBranches(self):
        """Prepare for using bzr branches."""
        self.useTempDir()
        server = FakeTransportServer(get_transport('.'))
        server.setUp()
        self.addCleanup(server.tearDown)


class TestStaticDiff(BzrTestCase):
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


class TestStaticDiffJob(BzrTestCase):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IStaticDiffJob, StaticDiffJob(
            1, from_revision_spec='0', to_revision_spec='1'))

    def test_run_revision_ids(self):
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.commit('First commit', rev_id='rev1')
        job = StaticDiffJob(branch=branch, from_revision_spec='0',
                            to_revision_spec='1')
        static_diff = job.run()
        self.assertEqual('null:', static_diff.from_revision_id)
        self.assertEqual('rev1', static_diff.to_revision_id)

    def test_run_diff_content(self):
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        open('file', 'wb').write('foo\n')
        tree.add('file')
        tree.commit('First commit')
        open('file', 'wb').write('bar\n')
        tree.commit('Next commit')
        job = StaticDiffJob(branch=branch, from_revision_spec='1',
                            to_revision_spec='2')
        static_diff = job.run()
        transaction.commit()
        static_diff.diff.diff_text.open()
        content_lines = static_diff.diff.diff_text.read().splitlines()
        self.assertEqual(
            ['@@ -1,1 +1,1 @@', '-foo', '+bar', ''], content_lines[3:])
        self.assertEqual(7, len(content_lines))

    def test_run_is_idempotent(self):
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.commit('First commit')
        job1 = StaticDiffJob(branch=branch, from_revision_spec='0',
                            to_revision_spec='1')
        static_diff1 = job1.run()
        job2 = StaticDiffJob(branch=branch, from_revision_spec='0',
                            to_revision_spec='1')
        static_diff2 = job2.run()
        self.assertTrue(static_diff1 is static_diff2)

    def test_run_sets_complete(self):
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.commit('First commit')
        job = StaticDiffJob(branch=branch, from_revision_spec='0',
                            to_revision_spec='1')
        job.run()
        self.assertEqual(JobStatus.COMPLETED, job.job.status)

    def test_destroySelf_destroys_job(self):
        branch = self.factory.makeBranch()
        static_diff_job = StaticDiffJob(branch=branch, from_revision_spec='0',
                                        to_revision_spec='1')
        job_id = static_diff_job.job.id
        static_diff_job.destroySelf()
        self.assertRaises(SQLObjectNotFound, Job.get, job_id)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
