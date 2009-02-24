#! /usr/bin/python2.4
# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Test the create_merge_proposals script"""

from cStringIO import StringIO
import unittest

import transaction
from zope.component import getUtility

from canonical.testing import ZopelessAppServerLayer
from canonical.launchpad.ftests import import_secret_test_key
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.scripts.tests import run_script
from canonical.launchpad.database.branchmergeproposal import (
    CreateMergeProposalJob)


class TestCreateMergeProposals(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_create_merge_proposals(self):
        """Ensure create_merge_proposals runs and creates proposals."""
        key = import_secret_test_key()
        email, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail(fingerprint=key.fingerprint))
        CreateMergeProposalJob.create(file_alias)
        self.assertEqual(0, source.landing_targets.count())
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/create_merge_proposals.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Ran 1 CreateMergeProposalJobs.\n', stderr)
        self.assertEqual('', stdout)
        self.assertEqual(1, source.landing_targets.count())

    def test_create_branch_and_proposals(self):
        """Ensure create_merge_proposals runs and creates proposals."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.branch.set_public_branch(branch.bzr_identity)
        tree.commit('rev1')
        source = tree.bzrdir.sprout('source').open_workingtree()
        source.commit('rev2')
        key = import_secret_test_key()
        message = self.factory.makeBundleMergeDirectiveEmail(
            source.branch, branch, key.fingerprint)
        message_string = message.as_string()
        file_alias = getUtility(ILibraryFileAliasSet).create(
            '*', len(message_string), StringIO(message_string), '*')
        CreateMergeProposalJob.create(file_alias)
        self.assertEqual(0, branch.landing_targets.count())
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/create_merge_proposals.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Ran 1 CreateMergeProposalJobs.\n', stderr)
        self.assertEqual('', stdout)
        self.assertEqual(1, targets.landing_targets.count())

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
