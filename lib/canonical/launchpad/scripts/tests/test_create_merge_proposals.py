#! /usr/bin/python2.4
# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Test the create_merge_proposals script"""

from cStringIO import StringIO
import unittest

from bzrlib import errors as bzr_errors
from bzrlib.branch import Branch
import transaction
from zope.component import getUtility

from canonical.testing import ZopelessAppServerLayer
from canonical.launchpad.ftests import import_secret_test_key
from lp.testing import TestCaseWithFactory
from lp.testing.factory import GPGSigningContext
from canonical.launchpad.scripts.tests import run_script
from lp.code.model.branchmergeproposal import (
    CreateMergeProposalJob)
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet


class TestCreateMergeProposals(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_create_merge_proposals(self):
        """Ensure create_merge_proposals runs and creates proposals."""
        key = import_secret_test_key()
        signing_context = GPGSigningContext(key.fingerprint, password='test')
        email, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail(
                signing_context=signing_context))
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

    def createJob(self, branch, tree):
        """Create merge directive job from this branch."""
        tree.branch.set_public_branch(branch.bzr_identity)
        tree.commit('rev1')
        source = tree.bzrdir.sprout('source').open_workingtree()
        source.commit('rev2')
        message = self.factory.makeBundleMergeDirectiveEmail(
            source.branch, branch)
        message_str = message.as_string()
        library_file_aliases = getUtility(ILibraryFileAliasSet)
        file_alias = library_file_aliases.create(
            '*', len(message_str), StringIO(message_str), '*')
        CreateMergeProposalJob.create(file_alias)
        return source

    def jobOutputCheck(self, branch, source):
        """Run the job and check the output."""
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/create_merge_proposals.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual(
            'INFO    creating lockfile\n'
            'INFO    Ran 1 CreateMergeProposalJobs.\n', stderr)
        self.assertEqual('', stdout)
        # The hosted location should be populated, not the mirror.
        bmp = branch.landing_candidates[0]
        self.assertRaises(
            bzr_errors.NotBranchError, Branch.open,
            bmp.source_branch.warehouse_url)
        local_source = Branch.open(bmp.source_branch.getPullURL())
        # The hosted branch has the correct last revision.
        self.assertEqual(
            source.branch.last_revision(), local_source.last_revision())
        # A mirror should be scheduled.
        self.assertIsNot(None, bmp.source_branch.next_mirror_time)

    def disabled_test_merge_directive_with_bundle(self):
        """Merge directives with bundles generate branches."""
        # XXX TimPenhey 2009-04-01 bug 352800
        self.useBzrBranches(real_server=True)
        branch, tree = self.create_branch_and_tree()
        source = self.createJob(branch, tree)
        self.jobOutputCheck(branch, source)

    def disabled_test_merge_directive_with_project(self):
        """Bundles are handled when the target branch has a project."""
        # XXX TimPenhey 2009-04-01 bug 352800
        self.useBzrBranches(real_server=True)
        product = self.factory.makeProduct(project=self.factory.makeProject())
        branch, tree = self.create_branch_and_tree(product=product)
        source = self.createJob(branch, tree)
        self.jobOutputCheck(branch, source)

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
