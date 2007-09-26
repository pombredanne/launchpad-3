import logging
import os
import shutil
import tempfile
import unittest

import bzrlib

from twisted.trial.unittest import TestCase as TrialTestCase 

from canonical.codehosting import branch_id_to_path
from canonical.config import config
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.scripts.supermirror.branchtomirror import (
    BranchToMirror)
from canonical.launchpad.scripts.supermirror.tests import createbranch
from canonical.launchpad.scripts.supermirror import jobmanager
from canonical.authserver.client.branchstatus import BranchStatusClient
from canonical.authserver.tests.harness import AuthserverTacTestSetup
from canonical.testing import LaunchpadFunctionalLayer, reset_logging


class TestJobManager(unittest.TestCase):

    def setUp(self):
        self.masterlock = 'master.lock'
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        reset_logging()

    def makeFakeClient(self, hosted, mirrored, imported):
        return FakeBranchStatusClient(
            {'HOSTED': hosted, 'MIRRORED': mirrored, 'IMPORTED': imported})

    def makeJobManager(self, branch_type, branch_tuples):
        if branch_type == BranchType.HOSTED:
            client = self.makeFakeClient(branch_tuples, [], [])
        elif branch_type == BranchType.MIRRORED:
            client = self.makeFakeClient([], branch_tuples, [])
        elif branch_type == BranchType.IMPORTED:
            client = self.makeFakeClient([], [], branch_tuples)
        else:
            self.fail("Unknown branch type: %r" % (branch_type,))
        return jobmanager.JobManager(client, branch_type)

    def testEmptyAddBranches(self):
        manager = self.makeJobManager(BranchType.HOSTED, [])
        self.assertEqual([], manager.branches_to_mirror)

    def testSingleAddBranches(self):
        # Get a list of branches and ensure that it can add a branch object.
        expected_branch = BranchToMirror(
            src='managersingle',
            dest=config.supermirror.branchesdest + '/00/00/00/00',
            branch_status_client=None, branch_id=None, unique_name=None,
            branch_type=None)
        manager = self.makeJobManager(
            BranchType.HOSTED, [(0, 'managersingle', u'name//trunk')])
        self.assertEqual([expected_branch], manager.branches_to_mirror)

    def testManagerCreatesLocks(self):
        try:
            manager = self.makeJobManager(BranchType.HOSTED, [])
            manager.lockfilename = self.masterlock
            manager.lock()
            self.failUnless(os.path.exists(self.masterlock))
            manager.unlock()
        finally:
            self._removeLockFile()

    def testManagerEnforcesLocks(self):
        try:
            manager = self.makeJobManager(BranchType.HOSTED, [])
            manager.lockfilename = self.masterlock
            manager.lock()
            anothermanager = self.makeJobManager(BranchType.HOSTED, [])
            anothermanager.lockfilename = self.masterlock
            self.assertRaises(jobmanager.LockError, anothermanager.lock)
            self.failUnless(os.path.exists(self.masterlock))
            manager.unlock()
        finally:
            self._removeLockFile()

    def _removeLockFile(self):
        if os.path.exists(self.masterlock):
            os.unlink(self.masterlock)

    def testImportAddBranches(self):
        import_manager = self.makeJobManager(
            BranchType.IMPORTED,
            [(14, 'http://escudero.ubuntu.com:680/0000000e',
              'vcs-imports//main')])
        expected_branch = BranchToMirror(
            src='http://escudero.ubuntu.com:680/0000000e',
            dest=config.supermirror.branchesdest + '/00/00/00/0e',
            branch_status_client=None, branch_id=None, unique_name=None,
            branch_type=None)
        self.assertEqual(import_manager.branches_to_mirror, [expected_branch])
        branch_types = [branch.branch_type
                        for branch in import_manager.branches_to_mirror]
        self.assertEqual(branch_types, [BranchType.IMPORTED])

    def testUploadAddBranches(self):
        upload_manager = self.makeJobManager(
            BranchType.HOSTED,
            [(25, '/tmp/sftp-test/branches/00/00/00/19', u'name12//pushed')])
        expected_branch = BranchToMirror(
            src='/tmp/sftp-test/branches/00/00/00/19',
            dest=config.supermirror.branchesdest + '/00/00/00/19',
            branch_status_client=None, branch_id=None, unique_name=None,
            branch_type=None)
        self.assertEqual(upload_manager.branches_to_mirror, [expected_branch])
        branch_types = [branch.branch_type
                        for branch in upload_manager.branches_to_mirror]
        self.assertEqual(branch_types, [BranchType.HOSTED])

    def testMirrorAddBranches(self):
        mirror_manager = self.makeJobManager(
            BranchType.MIRRORED,
            [(15, 'http://example.com/gnome-terminal/main', u'name12//main')])
        expected_branch = BranchToMirror(
            src='http://example.com/gnome-terminal/main',
            dest=config.supermirror.branchesdest + '/00/00/00/0f',
            branch_status_client=None, branch_id=None, unique_name=None,
            branch_type=None)
        self.assertEqual(mirror_manager.branches_to_mirror, [expected_branch])
        branch_types = [branch.branch_type
                        for branch in mirror_manager.branches_to_mirror]
        self.assertEqual(branch_types, [BranchType.MIRRORED])


class TestJobManagerInLaunchpad(TrialTestCase):
    layer = LaunchpadFunctionalLayer

    testdir = None

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        # Change the HOME environment variable in order to ignore existing
        # user config files.
        os.environ.update({'HOME': self.testdir})
        self.authserver = AuthserverTacTestSetup()
        self.authserver.setUp()

    def tearDown(self):
        shutil.rmtree(self.testdir)
        self.authserver.tearDown()

    def _getBranchDir(self, branchname):
        return os.path.join(self.testdir, branchname)

    def assertMirrored(self, branch_to_mirror):
        """Assert that branch_to_mirror's source and destinations have the same
        revisions.

        :param branch_to_mirror: a BranchToMirror instance.
        """
        source_branch = bzrlib.branch.Branch.open(branch_to_mirror.source)
        dest_branch = bzrlib.branch.Branch.open(branch_to_mirror.dest)
        self.assertEqual(source_branch.last_revision(),
                         dest_branch.last_revision())

    def testJobRunner(self):
        client = BranchStatusClient()
        manager = jobmanager.JobManager(client, BranchType.HOSTED)

        branches = [
            self._makeBranch("brancha", 1, client),
            self._makeBranch("branchb", 2, client),
            self._makeBranch("branchc", 3, client),
            self._makeBranch("branchd", 4, client),
            self._makeBranch("branche", 5, client)]
        manager.branches_to_mirror = list(branches)

        deferred = manager.run(logging.getLogger())

        def check_mirrored(ignored):
            self.assertEqual(len(manager.branches_to_mirror), 0)
            for branch in branches:
                self.assertMirrored(branch)

        return deferred.addCallback(check_mirrored)

    def _makeBranch(self, relativedir, target, branch_status_client):
        """Given a relative directory, make a strawman branch and return it.

        @param relativedir - The directory to make the branch
        @output BranchToMirror - A branch object representing the strawman
                                    branch
        """
        unique_name = '~testuser/+junk/' + relativedir
        branchdir = os.path.join(self.testdir, relativedir)
        createbranch(branchdir)
        if target == None:
            targetdir = None
        else:
            targetdir = os.path.join(self.testdir, branch_id_to_path(target))
        return BranchToMirror(
                branchdir, targetdir, branch_status_client, target,
                unique_name, branch_type=None)


class FakeBranchStatusClient:
    """A dummy branch status client implementation for testing getBranches()"""

    def __init__(self, branch_queues):
        self.branch_queues = branch_queues

    def getBranchPullQueue(self, branch_type):
        return self.branch_queues[branch_type]


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
