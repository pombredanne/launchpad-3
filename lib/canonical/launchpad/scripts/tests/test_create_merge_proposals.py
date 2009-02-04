#! /usr/bin/python2.4
# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Test the sendbranchmail script"""

import unittest
import transaction

from canonical.testing import ZopelessAppServerLayer
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.database.branchmergeproposal import (
    CreateMergeProposalJob)


class TestCreateMergeProposals(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_mpcreationjobs(self):
        """Ensure mpcreationjobs runs and generates diffs."""
        email, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail())
        CreateMergeProposalJob.create(file_alias)
        self.assertEqual(0, source.landing_targets.count())
        transaction.commit()
        self.assertEqual(1, len(list(CreateMergeProposalJob.iterReady())))
        retcode, stdout, stderr = run_script(
            'cronscripts/create_merge_proposals.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual('Ran 1 CreateMergeProposalJobs.\n', stdout)
        self.assertEqual('INFO    creating lockfile\n', stderr)
        self.assertEqual(1, source.landing_targets.count())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
