# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for branchtomirror.py."""

__metaclass__ = type

import httplib
import logging
import os
import shutil
import socket
import tempfile
import unittest
import urllib2

import bzrlib.branch
import bzrlib.bzrdir
import bzrlib.errors
from bzrlib.revision import NULL_REVISION
from bzrlib.tests import TestCaseInTempDir
from bzrlib.tests.repository_implementations.test_repository import (
            TestCaseWithRepository)
from bzrlib.transport import get_transport
from bzrlib.weave import Weave
from bzrlib.errors import (
    BzrError, UnsupportedFormatError, UnknownFormatError, ParamikoNotPresent,
    NotBranchError)

import transaction
from canonical.launchpad import database
from canonical.launchpad.scripts.supermirror_rewritemap import split_branch_id
from canonical.launchpad.scripts.supermirror.ftests import createbranch
from canonical.launchpad.scripts.supermirror.branchtomirror import (
    BranchToMirror)
from canonical.authserver.client.branchstatus import BranchStatusClient
from canonical.authserver.ftests.harness import AuthserverTacTestSetup
from canonical.testing import LaunchpadFunctionalLayer, reset_logging


class TestBranchToMirror(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    testdir = None

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        # Change the HOME environment variable in order to ignore existing
        # user config files.
        os.environ.update({'HOME': self.testdir})
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        shutil.rmtree(self.testdir)
        self.authserver.tearDown()

    def _getBranchDir(self, branchname):
        return os.path.join(self.testdir, branchname)

    def testMirror(self):
        # Create a branch
        srcbranchdir = self._getBranchDir("branchtomirror-testmirror-src")
        destbranchdir = self._getBranchDir("branchtomirror-testmirror-dest")

        client = BranchStatusClient()
        to_mirror = BranchToMirror(
            srcbranchdir, destbranchdir, client, 1, None)

        tree = createbranch(srcbranchdir)
        to_mirror.mirror(logging.getLogger())
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(tree.last_revision(),
                         mirrored_branch.last_revision())

        # make sure that the last mirrored revision is recorded
        transaction.abort()
        branch = database.Branch.get(1)
        self.assertEqual(branch.last_mirrored_id,
                         mirrored_branch.last_revision())

    def testMirrorEmptyBranch(self):
        # Check that we can mirror an empty branch, and that the
        # last_mirrored_id for an empty branch can be distinguished
        # from an unmirrored branch.
        
        # Create a branch
        srcbranchdir = self._getBranchDir("branchtomirror-testmirror-src")
        destbranchdir = self._getBranchDir("branchtomirror-testmirror-dest")

        client = BranchStatusClient()
        to_mirror = BranchToMirror(
            srcbranchdir, destbranchdir, client, 1, None)

        # create empty source branch
        os.makedirs(srcbranchdir)
        tree = bzrlib.bzrdir.BzrDir.create_standalone_workingtree(srcbranchdir)
        
        to_mirror.mirror(logging.getLogger())
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        self.assertEqual(None, mirrored_branch.last_revision())

        # make sure that the last mirrored revision is recorded as a string
        transaction.abort()
        branch = database.Branch.get(1)
        self.assertNotEqual(None, branch.last_mirrored_id)
        self.assertEqual(NULL_REVISION, branch.last_mirrored_id)


class TestBranchToMirrorFormats(TestCaseWithRepository):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBranchToMirrorFormats, self).setUp()
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        self.authserver.tearDown()
        super(TestBranchToMirrorFormats, self).tearDown()
        test_root = TestCaseInTempDir.TEST_ROOT
        if test_root is not None and os.path.exists(test_root):
            shutil.rmtree(test_root)
        # Set the TEST_ROOT back to None, to tell TestCaseInTempDir we need it
        # to create a new root when the next test is run.
        # The TestCaseInTempDir is part of bzr's test infrastructure and the
        # bzr test runner normally does this cleanup, but here we have to do
        # that ourselves.
        TestCaseInTempDir.TEST_ROOT = None

    def testMirrorKnitAsKnit(self):
        # Create a source branch in knit format, and check that the mirror is in
        # knit format.
        self.bzrdir_format = bzrlib.bzrdir.BzrDirMetaFormat1()
        self.repository_format = bzrlib.repository.RepositoryFormatKnit1()
        self._testMirrorFormat()

    def testMirrorMetaweaveAsMetaweave(self):
        # Create a source branch in metaweave format, and check that the mirror
        # is in metaweave format.
        self.bzrdir_format = bzrlib.bzrdir.BzrDirMetaFormat1()
        self.repository_format = bzrlib.repository.RepositoryFormat7()
        self._testMirrorFormat()

    def testMirrorWeaveAsWeave(self):
        # Create a source branch in weave format, and check that the mirror is
        # in weave format.
        self.bzrdir_format = bzrlib.bzrdir.BzrDirFormat6()
        self.repository_format = bzrlib.repository.RepositoryFormat6()
        self._testMirrorFormat()

    def testSourceFormatChange(self):
        # Create and mirror a branch in weave format.
        self.bzrdir_format = bzrlib.bzrdir.BzrDirMetaFormat1()
        self.repository_format = bzrlib.repository.RepositoryFormat7()
        self._createSourceBranch()
        self._mirror()
        
        # Change the branch to knit format.
        shutil.rmtree('src-branch')
        self.repository_format = bzrlib.repository.RepositoryFormatKnit1()
        self._createSourceBranch()

        # Mirror again.  The mirrored branch should now be in knit format.
        mirrored_branch = self._mirror()
        self.assertEqual(
            self.repository_format.get_format_description(),
            mirrored_branch.repository._format.get_format_description())

    def _createSourceBranch(self):
        os.mkdir('src-branch')
        tree = self.make_branch_and_tree('src-branch')
        self.local_branch = tree.branch
        self.build_tree(['foo'], transport=get_transport('./src-branch'))
        tree.add('foo')
        tree.commit('Added foo', rev_id='rev1')
        return tree

    def _mirror(self):
        # Mirror src-branch to dest-branch
        client = BranchStatusClient()
        to_mirror = BranchToMirror(
            'src-branch', 'dest-branch', client, 1, None)
        to_mirror.mirror(logging.getLogger())
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        return mirrored_branch

    def _testMirrorFormat(self):
        tree = self._createSourceBranch()
        
        mirrored_branch = self._mirror()
        self.assertEqual(tree.last_revision(),
                         mirrored_branch.last_revision())

        # Assert that the mirrored branch is in source's format
        # XXX AndrewBennetts 2006-05-18: comparing format objects is ugly.
        # See bug 45277.
        self.assertEqual(
            self.repository_format.get_format_description(),
            mirrored_branch.repository._format.get_format_description())
        self.assertEqual(
            self.bzrdir_format.get_format_description(),
            mirrored_branch.bzrdir._format.get_format_description())


class TestBranchToMirror_SourceProblems(TestCaseInTempDir):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        TestCaseInTempDir.setUp(self)
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        self.authserver.tearDown()
        TestCaseInTempDir.tearDown(self)
        test_root = TestCaseInTempDir.TEST_ROOT
        if test_root is not None and os.path.exists(test_root):
            shutil.rmtree(test_root)
        # Set the TEST_ROOT back to None, to tell TestCaseInTempDir we need it
        # to create a new root when the next test is run.
        # The TestCaseInTempDir is part of bzr's test infrastructure and the
        # bzr test runner normally does this cleanup, but here we have to do
        # that ourselves.
        TestCaseInTempDir.TEST_ROOT = None

    def testUnopenableSourceDoesNotCreateMirror(self):
        non_existant_branch = "nonsensedir"
        dest_dir = "dest-dir"
        client = BranchStatusClient()
        mybranch = BranchToMirror(
            non_existant_branch, dest_dir, client, 1, 'foo/bar/baz')
        mybranch.mirror(logging.getLogger())
        self.failIf(os.path.exists(dest_dir), 'dest-dir should not exist')

    def testMissingSourceWhines(self):
        non_existant_branch = "nonsensedir"
        client = BranchStatusClient()
        # ensure that we have no errors muddying up the test
        client.mirrorComplete(1, NULL_REVISION)
        mybranch = BranchToMirror(
            non_existant_branch, "anothernonsensedir", client, 1,
            'foo/bar/baz')
        mybranch.mirror(logging.getLogger())
        transaction.abort()
        branch = database.Branch.get(1)
        self.assertEqual(1, branch.mirror_failures)

    def testMissingFileRevisionData(self):
        self.build_tree(['missingrevision/',
                         'missingrevision/afile'])
        tree = bzrlib.bzrdir.BzrDir.create_standalone_workingtree(
            'missingrevision')
        tree.add(['afile'], ['myid'])
        tree.commit('start')
        # now we have a good branch with a file called afile and id myid
        # we need to figure out the actual path for the weave.. or 
        # deliberately corrupt it. like this.
        tree.branch.repository.weave_store.put_weave(
            "myid", Weave(weave_name="myid"),
            tree.branch.repository.get_transaction())
        # now try mirroring this branch.
        client = BranchStatusClient()
        # clear the error status
        client.mirrorComplete(1, NULL_REVISION)
        mybranch = BranchToMirror(
            'missingrevision', "missingrevisiontarget", client, 1,
            'foo/bar/baz')
        mybranch.mirror(logging.getLogger())
        transaction.abort()
        branch = database.Branch.get(1)
        self.assertEqual(1, branch.mirror_failures)


class TestErrorHandling(unittest.TestCase):

    def setUp(self):
        client = BranchStatusClient()
        self.branch = BranchToMirror(
            'foo', 'bar', client, 1, 'owner/product/foo')
        # Stub out everything that we don't need to test
        client.startMirroring = lambda branch_id: None
        self.branch._mirrorFailed = lambda logger, err: self.errors.append(err)
        self.branch._openSourceBranch = lambda: None
        self.branch._mirrorToDestBranch = lambda: None
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)
        self.errors = []

    def tearDown(self):
        reset_logging()

    def _runMirrorAndCheckError(self, expected_error):
        """Run mirror and check that we receive exactly one error, the str() of
        which starts with `expected_error`.
        """
        self.branch.mirror(logging.getLogger())
        self.assertEqual(len(self.errors), 1)
        error = str(self.errors[0])
        if not error.startswith(expected_error):
            self.fail('Expected "%s" but got "%s"' % (expected_error, error))
        return error

    def testHTTPError(self):
        def stubOpenSourceBranch():
            raise urllib2.HTTPError(
                'http://something', httplib.UNAUTHORIZED, 
                'Authorization Required', 'some headers',
                open(tempfile.mkstemp()[1]))
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'Private branch; required authentication'
        self._runMirrorAndCheckError(expected_msg)

    def testSocketErrorHandling(self):
        def stubOpenSourceBranch():
            raise socket.error('foo')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'A socket error occurred:'
        self._runMirrorAndCheckError(expected_msg)

    def testUnsupportedFormatErrorHandling(self):
        def stubOpenSourceBranch():
            raise UnsupportedFormatError('Bazaar-NG branch, format 0.0.4')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'The supermirror does not support branches'
        self._runMirrorAndCheckError(expected_msg)

    def testUnknownFormatError(self):
        def stubOpenSourceBranch():
            raise UnknownFormatError(format='Bad format')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'Unknown branch format:'
        self._runMirrorAndCheckError(expected_msg)

    def testParamikoNotPresent(self):
        def stubOpenSourceBranch():
            raise ParamikoNotPresent('No module named paramiko')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'The supermirror does not support mirroring branches'
        self._runMirrorAndCheckError(expected_msg)

    def testNotBranchError(self):
        # Should receive a user-friendly message we are asked to mirror a
        # non-branch.
        def stubOpenSourceBranch():
            raise NotBranchError('/foo/baz/')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'Not a branch:'
        self._runMirrorAndCheckError(expected_msg)

    def testNotBranchErrorGivesURL(self):
        # The not-a-branch error message should *not* include the Branch id
        # from the database. Instead, the path should be translated to a
        # user-visible location.
        split_id = split_branch_id(self.branch.branch_id)
        def stubOpenSourceBranch():
            raise NotBranchError('/srv/sm-ng/push-branches/%s/.bzr/branch/'
                                 % split_id)
        self.branch._openSourceBranch = stubOpenSourceBranch
        observed_msg = self._runMirrorAndCheckError('Not a branch:')
        self.failIf(split_id in observed_msg,
                    "%r in %r" % (split_id, observed_msg))
        url = ('sftp://bazaar.launchpad.net/~%s'
               % self.branch.branch_unique_name)
        self.assertEqual('Not a branch: %s' % url, observed_msg)

    def testBzrErrorHandling(self):
        def stubOpenSourceBranch():
            raise BzrError('A generic bzr error')
        self.branch._openSourceBranch = stubOpenSourceBranch
        expected_msg = 'A generic bzr error'
        self._runMirrorAndCheckError(expected_msg)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
