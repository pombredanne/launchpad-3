import logging
import os
import shutil
import socket
from StringIO import StringIO
import tempfile
import unittest

import bzrlib.branch
import bzrlib.errors
from bzrlib.tests import TestCaseInTempDir
from bzrlib.weave import Weave

import transaction
from canonical.testing import reset_logging
from canonical.launchpad import database
from canonical.launchpad.scripts.supermirror.ftests import createbranch
from canonical.launchpad.scripts.supermirror.branchtomirror import (
    BranchToMirror)
from canonical.authserver.client.branchstatus import BranchStatusClient
from canonical.authserver.ftests.harness import AuthserverTacTestSetup
from canonical.launchpad.ftests.harness import (
    LaunchpadFunctionalTestSetup, LaunchpadFunctionalTestCase)
from canonical.functional import FunctionalLayer


class TestBranchToMirror(LaunchpadFunctionalTestCase):
    layer = FunctionalLayer

    testdir = None

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        LaunchpadFunctionalTestCase.setUp(self)
        # Change the HOME environment variable in order to ignore existing
        # user config files.
        os.environ.update({'HOME': self.testdir})
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()

    def tearDown(self):
        shutil.rmtree(self.testdir)
        self.authserver.tearDown()
        LaunchpadFunctionalTestCase.tearDown(self)

    def _getBranchDir(self, branchname):
        return os.path.join(self.testdir, branchname)

    def testMirror(self):
        # Create a branch
        srcbranchdir = self._getBranchDir("branchtomirror-testmirror-src")
        destbranchdir = self._getBranchDir("branchtomirror-testmirror-dest")

        client = BranchStatusClient()
        to_mirror = BranchToMirror(srcbranchdir, destbranchdir, client, 1)

        tree = createbranch(srcbranchdir)
        to_mirror.mirror()
        mirrored_tree = bzrlib.workingtree.WorkingTree.open(to_mirror.dest)
        self.assertEqual(tree.last_revision(), mirrored_tree.last_revision())


class TestBranchToMirror_SourceProblems(TestCaseInTempDir):
    layer = FunctionalLayer

    def setUp(self):
        LaunchpadFunctionalTestSetup().setUp()
        TestCaseInTempDir.setUp(self)
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()

    def tearDown(self):
        self.authserver.tearDown()
        TestCaseInTempDir.tearDown(self)
        LaunchpadFunctionalTestSetup().tearDown()
        test_root = TestCaseInTempDir.TEST_ROOT
        if test_root is not None and os.path.exists(test_root):
            shutil.rmtree(test_root)
        # Set the TEST_ROOT back to None, to tell TestCaseInTempDir we need it
        # to create a new root when the next test is run.
        # The TestCaseInTempDir is part of bzr's test infrastructure and the
        # bzr test runner normally does this cleanup, but here we have to do
        # that ourselves.
        TestCaseInTempDir.TEST_ROOT = None

    def testMissingSourceWhines(self):
        non_existant_branch = "/nonsensedir"
        client = BranchStatusClient()
        # ensure that we have no errors muddying up the test
        client.mirrorComplete(1)
        mybranch = BranchToMirror(
            non_existant_branch, "/anothernonsensedir", client, 1)
        mybranch.mirror()
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
        client.mirrorComplete(1)
        mybranch = BranchToMirror(
            'missingrevision', "missingrevisiontarget", client, 1)
        mybranch.mirror()
        transaction.abort()
        branch = database.Branch.get(1)
        if branch.mirror_failures == 0:
            # XXX: Open a bug on this instead of generating noise
            # -- StuartBishop 20060329
            # print >> sys.stderr, (
            #     "canonical.launchpad.scripts.supermirror.tests."
            #     "test_branchtomirror.testMissingFileRevisionData "
            #     "disabled until bzr is updated to correctly detect "
            #     "this corruption.")
            pass
        else:
            # XXX: Open a bug on this instead of generating noise
            # -- StuartBishop 20060329
            # print >> sys.stderr, (
            #     "canonical.launchpad.scripts.supermirror.tests."
            #     "test_branchtomirror.testMissingFileRevisionData appears "
            #     "to work now bzr is updated, please remove the 'bzr needs "
            #     "updating' warning messages.")
            self.assertEqual(1, branch.mirror_failures)


class TestErrorHandling(unittest.TestCase):

    def setUp(self):
        # Set up a mock logger so we don't generate noise on stdout.
        logger = logging.getLogger('branch-puller')
        logger.propagate = 0
        self.mock_handler = logging.StreamHandler(StringIO())
        logger.addHandler(self.mock_handler)
        self.errors = []
        client = BranchStatusClient()
        self.branch = BranchToMirror('foo', 'bar', client, 1)
        # Stub out everything that we don't need to test
        client.startMirroring = lambda branch_id: None
        self.branch._mirrorFailed = lambda err: self.errors.append(err)
        self.branch._openSourceBranch = lambda: None
        self.branch._openDestBranch = lambda: None
        self.branch._pullSourceToDest = lambda: None

    def tearDown(self):
        logger = logging.getLogger('branch-puller')
        logger.removeHandler(self.mock_handler)
        reset_logging()

    def _runMirrorAndCheckError(self, error_type):
        self.branch.mirror()
        self.assertEqual(len(self.errors), 1)
        self.assertTrue(isinstance(self.errors[0], error_type))

    def testSourceBranchSocketErrorHandling(self):
        self.errors = []
        def stubOpenSourceBranch():
            raise socket.error('foo')
        self.branch._openSourceBranch = stubOpenSourceBranch
        self._runMirrorAndCheckError(socket.error)

    def testSourceBranchBzrErrorHandling(self):
        self.errors = []
        def stubOpenSourceBranch():
            raise bzrlib.errors.BzrError('foo')
        self.branch._openSourceBranch = stubOpenSourceBranch
        self._runMirrorAndCheckError(bzrlib.errors.BzrError)

    def testPullSocketErrorandling(self):
        self.errors = []
        def stubPullSourceToDest():
            raise socket.error('foo')
        self.branch._pullSourceToDest = stubPullSourceToDest
        self._runMirrorAndCheckError(socket.error)

    def testPullBzrErrorandling(self):
        self.errors = []
        def stubPullSourceToDest():
            raise bzrlib.errors.BzrError('foo')
        self.branch._pullSourceToDest = stubPullSourceToDest
        self._runMirrorAndCheckError(bzrlib.errors.BzrError)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
