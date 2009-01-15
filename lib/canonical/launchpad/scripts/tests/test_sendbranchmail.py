#! /usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test the sendbranchmail script"""

import unittest
import transaction

from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.interfaces import (
    BranchSubscriptionNotificationLevel, BranchSubscriptionDiffSize,
    CodeReviewNotificationLevel,)
from canonical.launchpad.database import RevisionMailJob


class TestSendbranchmail(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_sendbranchmail(self):
        branch = self.factory.makeBranch()
        branch.subscribe(branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL)
        job_1 = RevisionMailJob.create(
            branch, 0, 'from@example.org', 'body', False, 'foo')
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/sendbranchmail.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual('Ran 1 RevisionMailJobs.\n', stdout)
        self.assertEqual('', stderr)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
