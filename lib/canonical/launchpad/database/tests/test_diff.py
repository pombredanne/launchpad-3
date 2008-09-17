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

    def create_bzr_branch(self, db_branch):
        transport = get_transport(db_branch.warehouse_url)
        transport.clone('../..').ensure_base()
        transport.clone('..').ensure_base()
        return BzrDir.create_branch_convenience(db_branch.warehouse_url)

    def test_run(self):
        self.useTempDir()
        branch = self.factory.makeBranch()
        job = StaticDiffJob(branch=branch, from_revision_spec='0',
                            to_revision_spec='1')
        server = FakeTransportServer(get_transport('.'))
        server.setUp()
        try:
            bzr_branch = self.create_bzr_branch(branch)
            tree = bzr_branch.create_checkout('.')
            tree.commit('First commit', rev_id='rev1')
            static_diff = job.run()
        finally:
            server.tearDown()
        self.assertEqual('null:', static_diff.from_revision_id)
        self.assertEqual('rev1', static_diff.to_revision_id)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
