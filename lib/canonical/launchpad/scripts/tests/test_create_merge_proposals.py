#! /usr/bin/python2.4
# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Test the create_merge_proposals script"""

import os
import unittest

import transaction

from canonical.testing import ZopelessAppServerLayer
from canonical.launchpad.ftests import import_secret_test_key
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.database.branchmergeproposal import (
    CreateMergeProposalJob)


class TestCreateMergeProposals(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_create_merge_proposals(self):
        """Ensure create_merge_proposals runs and creates proposals."""
        key = import_secret_test_key('foo.bar@canonical.com-passwordless.sec')
        email, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail(fingerprint=key.fingerprint))
        CreateMergeProposalJob.create(file_alias)
        self.assertEqual(0, source.landing_targets.count())
        transaction.commit()
        env = dict(os.environ)
        env['import_public_test_keys'] = '1'
        retcode, stdout, stderr = run_script(
            'cronscripts/create_merge_proposals.py', [], env=env)
        self.assertEqual(0, retcode)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Ran 1 CreateMergeProposalJobs.\n', stderr)
        self.assertEqual('', stdout)
        self.assertEqual(1, source.landing_targets.count())

    def test_oops(self):
        """A bogus request should cause an oops, not an exception."""
        file_alias = self.factory.makeLibraryFileAlias('bogus')
        CreateMergeProposalJob.create(file_alias)
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/create_merge_proposals.py', [])
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Ran 0 CreateMergeProposalJobs.\n', stderr)
        self.assertEqual('', stdout)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
