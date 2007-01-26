import logging
import os
import shutil
import tempfile
import unittest

import bzrlib

from canonical.config import config
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.launchpad.scripts.supermirror.branchtomirror import (
    BranchToMirror)
from canonical.launchpad.scripts.supermirror.branchtargeter import branchtarget
from canonical.launchpad.scripts.supermirror.ftests import createbranch
from canonical.launchpad.scripts.supermirror import jobmanager
from canonical.authserver.client.branchstatus import BranchStatusClient
from canonical.authserver.ftests.harness import AuthserverTacTestSetup
from canonical.testing import LaunchpadFunctionalLayer, reset_logging


class TestJobManager(unittest.TestCase):

    def setUp(self):
        self.masterlock = 'master.lock'
        # We set the log level to CRITICAL so that the log messages
        # are suppressed.
        logging.basicConfig(level=logging.CRITICAL)

    def tearDown(self):
        reset_logging()

    def testExistance(self):
        from canonical.launchpad.scripts.supermirror.jobmanager import (
            JobManager)
        assert JobManager

    def testEmptyAddBranches(self):
        fakeclient = FakeBranchStatusClient([])
        manager = jobmanager.JobManager()
        manager.addBranches(fakeclient)
        self.assertEqual([], manager.branches_to_mirror)

    def testSingleAddBranches(self):
        # Get a list of branches and ensure that it can add a branch object.
        expected_branch = BranchToMirror(
            'managersingle', config.supermirror.branchesdest + '/00/00/00/00',
            None, None)
        fakeclient = FakeBranchStatusClient([
            (0, 'managersingle'),
            ])
        manager = jobmanager.JobManager()
        manager.addBranches(fakeclient)
        self.assertEqual([expected_branch], manager.branches_to_mirror)

    def testAddJobManager(self):
        manager = jobmanager.JobManager()
        manager.add(BranchToMirror('foo', 'bar', None, None))
        manager.add(BranchToMirror('baz', 'bar', None, None))
        self.assertEqual(len(manager.branches_to_mirror), 2)

    def testManagerCreatesLocks(self):
        try:
            self._removeLockFile()
            manager = jobmanager.JobManager()
            manager.lock(lockfilename=self.masterlock)
            self.failUnless(os.path.exists(self.masterlock))
            manager.unlock()
        finally:
            self._removeLockFile()

    def testManagerEnforcesLocks(self):
        try:
            self._removeLockFile()
            manager = jobmanager.JobManager()
            manager.lock(lockfilename=self.masterlock)
            anothermanager = jobmanager.JobManager()
            self.assertRaises(jobmanager.LockError, anothermanager.lock)
            self.failUnless(os.path.exists(self.masterlock))
            manager.unlock()
        finally:
            self._removeLockFile()

    def _removeLockFile(self):
        if os.path.exists(self.masterlock):
            os.unlink(self.masterlock)


class TestJobManagerInLaunchpad(unittest.TestCase):
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
        manager = jobmanager.JobManager()
        self.assertEqual(len(manager.branches_to_mirror), 0)

        client = BranchStatusClient()
        brancha = self._makeBranch("brancha", 1, client)
        manager.add(brancha)

        branchb = self._makeBranch("branchb", 2, client)
        manager.add(branchb)

        branchc = self._makeBranch("branchc", 3, client)
        manager.add(branchc)

        branchd = self._makeBranch("branchd", 4, client)
        manager.add(branchd)

        branche = self._makeBranch("branche", 5, client)
        manager.add(branche)

        self.assertEqual(len(manager.branches_to_mirror), 5)

        manager.run(logging.getLogger())

        self.assertEqual(len(manager.branches_to_mirror), 0)
        self.assertMirrored(brancha)
        self.assertMirrored(branchb)
        self.assertMirrored(branchc)
        self.assertMirrored(branchd)
        self.assertMirrored(branche)

    def _makeBranch(self, relativedir, target, branch_status_client):
        """Given a relative directory, make a strawman branch and return it.

        @param relativedir - The directory to make the branch
        @output BranchToMirror - A branch object representing the strawman
                                    branch
        """
        branchdir = os.path.join(self.testdir, relativedir)
        createbranch(branchdir)
        if target == None:
            targetdir = None
        else:
            targetdir = os.path.join(self.testdir, branchtarget(target))
        return BranchToMirror(
                branchdir, targetdir, branch_status_client, target
                )


class FakeBranchStatusClient:
    """A dummy branch status client implementation for testing getBranches()"""

    def __init__(self, branches_to_pull):
        self.branches_to_pull = branches_to_pull

    def getBranchPullQueue(self):
        return self.branches_to_pull


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

