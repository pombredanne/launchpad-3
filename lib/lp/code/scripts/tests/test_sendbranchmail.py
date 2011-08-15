#! /usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the sendbranchmail script"""

import transaction

from canonical.launchpad.scripts.tests import run_script
from canonical.testing.layers import ZopelessAppServerLayer
from lp.code.enums import (
    BranchSubscriptionDiffSize,
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.code.model.branchjob import (
    RevisionMailJob,
    RevisionsAddedJob,
    )
from lp.services.osutils import override_environ
from lp.testing import TestCaseWithFactory


class TestSendbranchmail(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def createBranch(self):
        branch, tree = self.create_branch_and_tree()
        branch.subscribe(
            branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL,
            branch.registrant)
        transport = tree.bzrdir.root_transport
        transport.put_bytes('foo', 'bar')
        tree.add('foo')
        # XXX: AaronBentley 2010-08-06 bug=614404: a bzr username is
        # required to generate the revision-id.
        with override_environ(BZR_EMAIL='me@example.com'):
            tree.commit('Added foo.', rev_id='rev1')
        return branch, tree

    def test_sendbranchmail(self):
        """Ensure sendbranchmail runs and sends email."""
        self.useBzrBranches()
        branch, tree = self.createBranch()
        mail_job = RevisionMailJob.create(
            branch, 1, 'from@example.org', 'body', True, 'foo')
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/sendbranchmail.py', [])
        self.assertEqual(
            'INFO    Creating lockfile: /var/lock/launchpad-sendbranchmail.lock\n'
            'INFO    Running RevisionMailJob (ID %d) in status Waiting\n'
            'INFO    Ran 1 RevisionMailJobs.\n' % mail_job.job.id, stderr)
        self.assertEqual('', stdout)
        self.assertEqual(0, retcode)

    def test_sendbranchmail_handles_oops(self):
        """Ensure sendbranchmail runs and sends email."""
        self.useTempBzrHome()
        branch = self.factory.makeBranch()
        RevisionMailJob.create(
            branch, 1, 'from@example.org', 'body', True, 'foo')
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/sendbranchmail.py', [])
        self.assertIn(
            'INFO    Creating lockfile: /var/lock/launchpad-sendbranchmail.lock\n',
            stderr)
        self.assertIn('INFO    Job resulted in OOPS:', stderr)
        self.assertIn('INFO    Ran 0 RevisionMailJobs.\n', stderr)
        self.assertEqual('', stdout)
        self.assertEqual(0, retcode)

    def test_revision_added_job(self):
        """RevisionsAddedJobs are run by sendbranchmail."""
        self.useBzrBranches()
        branch, tree = self.createBranch()
        tree.bzrdir.root_transport.put_bytes('foo', 'baz')
        # XXX: AaronBentley 2010-08-06 bug=614404: a bzr username is
        # required to generate the revision-id.
        with override_environ(BZR_EMAIL='me@example.com'):
            tree.commit('Added foo.', rev_id='rev2')
        job = RevisionsAddedJob.create(
            branch, 'rev1', 'rev2', 'from@example.org')
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/sendbranchmail.py', [])
        self.assertEqual(
            'INFO    Creating lockfile: /var/lock/launchpad-sendbranchmail.lock\n'
            'INFO    Running RevisionsAddedJob (ID %d) in status Waiting\n'
            'INFO    Ran 1 RevisionMailJobs.\n' % job.job.id,
            stderr)
        self.assertEqual('', stdout)
        self.assertEqual(0, retcode)
