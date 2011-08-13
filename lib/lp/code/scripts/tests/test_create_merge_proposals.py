#! /usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the create_merge_proposals script"""

from cStringIO import StringIO

from bzrlib import errors as bzr_errors
from bzrlib.branch import Branch
import transaction
from zope.component import getUtility

from canonical.launchpad.ftests import import_secret_test_key
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.scripts.tests import run_script
from canonical.testing.layers import ZopelessAppServerLayer
from lp.code.model.branchmergeproposaljob import CreateMergeProposalJob
from lp.testing import TestCaseWithFactory
from lp.testing.factory import GPGSigningContext


class TestCreateMergeProposals(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_create_merge_proposals(self):
        """Ensure create_merge_proposals runs and creates proposals."""
        key = import_secret_test_key()
        signing_context = GPGSigningContext(key.fingerprint, password='test')
        email, file_alias, source, target = (
            self.factory.makeMergeDirectiveEmail(
                signing_context=signing_context))
        job = CreateMergeProposalJob.create(file_alias)
        self.assertEqual(0, source.landing_targets.count())
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/create_merge_proposals.py', [])
        self.assertEqual(0, retcode)
        self.assertEqual(
            'INFO    Creating lockfile: /var/lock/launchpad-create_merge_proposals.lock\n'
            'INFO    Running CreateMergeProposalJob (ID %d) in status Waiting\n'
            'INFO    Ran 1 CreateMergeProposalJobs.\n' % job.job.id, stderr)
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
            'INFO    Creating lockfile: /var/lock/launchpad-create_merge_proposals.lock\n'
            'INFO    Ran 1 CreateMergeProposalJobs.\n', stderr)
        self.assertEqual('', stdout)
        bmp = branch.landing_candidates[0]
        local_source = bmp.source_branch.getBzrBranch()
        # The branch has the correct last revision.
        self.assertEqual(
            source.branch.last_revision(), local_source.last_revision())

    def disabled_test_merge_directive_with_bundle(self):
        """Merge directives with bundles generate branches."""
        # XXX TimPenhey 2009-04-01 bug 352800
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        source = self.createJob(branch, tree)
        self.jobOutputCheck(branch, source)

    def disabled_test_merge_directive_with_project(self):
        """Bundles are handled when the target branch has a project."""
        # XXX TimPenhey 2009-04-01 bug 352800
        self.useBzrBranches()
        product = self.factory.makeProduct(project=self.factory.makeProject())
        branch, tree = self.create_branch_and_tree(product=product)
        source = self.createJob(branch, tree)
        self.jobOutputCheck(branch, source)

    def test_oops(self):
        """A bogus request should cause an oops, not an exception."""
        file_alias = self.factory.makeLibraryFileAlias(content='bogus')
        CreateMergeProposalJob.create(file_alias)
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/create_merge_proposals.py', [])
        self.assertIn('INFO    Creating lockfile:', stderr)
        self.assertIn('INFO    Job resulted in OOPS:', stderr)
        self.assertIn('INFO    Ran 0 CreateMergeProposalJobs.\n', stderr)
        self.assertEqual('', stdout)
