# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for Job-running facilities."""


from unittest import TestLoader

from canonical.testing import LaunchpadZopelessLayer

from canonical.config import config
from lp.services.job.runner import JobRunner
from lp.code.model.branchjob import RevisionMailJob
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel)
from canonical.launchpad.database.diff import StaticDiff
from lp.code.interfaces.branchsubscription import (
    BranchSubscriptionDiffSize,)
from canonical.launchpad.testing import TestCaseWithFactory


class TestRevisionMailJob(TestCaseWithFactory):
    """Ensure RevisionMailJob behaves as expected."""

    layer = LaunchpadZopelessLayer

    def test_runJob_generates_diff(self):
        """Ensure that a diff is actually generated in this environment."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        branch.subscribe(branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL)
        tree_transport = tree.bzrdir.root_transport
        tree_transport.put_bytes("hello.txt", "Hello World\n")
        tree.add('hello.txt')
        to_revision_id = tree.commit('rev1', timestamp=1e9, timezone=0)
        job = RevisionMailJob.create(
            branch, 1, 'from@example.org', 'body', True, 'subject')
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(config.sendbranchmail.dbuser)
        runner = JobRunner(job)
        runner.runJob(job)
        existing_diff = StaticDiff.selectOneBy(
            from_revision_id='null:', to_revision_id=to_revision_id)
        self.assertIsNot(None, existing_diff)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
