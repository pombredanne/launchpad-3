# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Job-running facilities."""

from canonical.config import config
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.code.model.branchjob import RevisionMailJob
from lp.code.model.diff import StaticDiff
from lp.services.job.runner import JobRunner
from lp.services.osutils import override_environ
from lp.testing import TestCaseWithFactory


class TestRevisionMailJob(TestCaseWithFactory):
    """Ensure RevisionMailJob behaves as expected."""

    layer = LaunchpadZopelessLayer

    def test_runJob_generates_diff(self):
        """Ensure that a diff is actually generated in this environment."""
        self.useBzrBranches(direct_database=True)
        branch, tree = self.create_branch_and_tree()
        branch.subscribe(branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL, branch.registrant)
        tree_transport = tree.bzrdir.root_transport
        tree_transport.put_bytes("hello.txt", "Hello World\n")
        tree.add('hello.txt')
        # XXX: AaronBentley 2010-08-06 bug=614404: a bzr username is
        # required to generate the revision-id.
        with override_environ(BZR_EMAIL='me@example.com'):
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
