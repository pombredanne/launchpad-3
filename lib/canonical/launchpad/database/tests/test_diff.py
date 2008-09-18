# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Diff, etc."""

__metaclass__ = type


from unittest import TestLoader

from bzrlib.bzrdir import BzrDir
from bzrlib.transport import get_transport
from canonical.testing import LaunchpadZopelessLayer

from canonical.codehosting.scanner.tests.test_bzrsync import FakeTransportServer
from canonical.launchpad.database.diff import *
from canonical.launchpad.interfaces import IDiff, IStaticDiff, IStaticDiffJob
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.testing import verifyObject


class TestDiff(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IDiff, Diff())


class BzrTestCase(TestCaseWithFactory):

    def create_branch_and_tree(self, tree_location='.'):
        db_branch = self.factory.makeBranch()
        transport = get_transport(db_branch.warehouse_url)
        transport.clone('../..').ensure_base()
        transport.clone('..').ensure_base()
        bzr_branch = BzrDir.create_branch_convenience(db_branch.warehouse_url)
        return db_branch, bzr_branch.create_checkout(tree_location)

    def useBzrBranches(self):
        self.useTempDir()
        server = FakeTransportServer(get_transport('.'))
        server.setUp()
        self.addCleanup(server.tearDown)



class TestStaticDiff(BzrTestCase):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IStaticDiff, StaticDiff())

    def test_acquire_existing(self):
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.commit('First commit', rev_id='rev1')
        diff1 = StaticDiff.acquire('null:', 'rev1', tree.branch.repository)
        diff2 = StaticDiff.acquire('null:', 'rev1', tree.branch.repository)
        self.assertTrue(diff1 is diff2)

    def test_acquire_existing_different_repo(self):
        self.useBzrBranches()
        branch1, tree1 = self.create_branch_and_tree('tree1')
        tree1.commit('First commit', rev_id='rev1')
        branch2, tree2 = self.create_branch_and_tree('tree2')
        tree2.pull(tree1.branch)
        diff1 = StaticDiff.acquire('null:', 'rev1', tree1.branch.repository)
        diff2 = StaticDiff.acquire('null:', 'rev1', tree2.branch.repository)
        self.assertTrue(diff1 is diff2)

    def test_acquire_nonexisting(self):
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.commit('First commit', rev_id='rev1')
        tree.commit('Next commit', rev_id='rev2')
        diff1 = StaticDiff.acquire('null:', 'rev1', tree.branch.repository)
        diff2 = StaticDiff.acquire('rev1', 'rev2', tree.branch.repository)
        self.assertFalse(diff1 is diff2)


class TestStaticDiffJob(BzrTestCase):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IStaticDiffJob, StaticDiffJob())

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
        import transaction
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


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
