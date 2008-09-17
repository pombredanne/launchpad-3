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


class TestStaticDiff(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IStaticDiff, StaticDiff())


class TestStaticDiffJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IStaticDiffJob, StaticDiffJob())

    def create_branch_and_tree(self, db_branch):
        transport = get_transport(db_branch.warehouse_url)
        transport.clone('../..').ensure_base()
        transport.clone('..').ensure_base()
        bzr_branch = BzrDir.create_branch_convenience(db_branch.warehouse_url)
        return bzr_branch.create_checkout('.')

    def useBzrBranches(self):
        self.useTempDir()
        server = FakeTransportServer(get_transport('.'))
        server.setUp()
        self.addCleanup(server.tearDown)

    def test_run_revision_ids(self):
        self.useBzrBranches()
        branch = self.factory.makeBranch()
        tree = self.create_branch_and_tree(branch)
        tree.commit('First commit', rev_id='rev1')
        job = StaticDiffJob(branch=branch, from_revision_spec='0',
                            to_revision_spec='1')
        static_diff = job.run()
        self.assertEqual('null:', static_diff.from_revision_id)
        self.assertEqual('rev1', static_diff.to_revision_id)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
