import os
import shutil
import signal
import tempfile
import unittest

from canonical.launchpad.scripts.supermirror.bzr_5_6 import BZR_5_6
from canonical.launchpad.scripts.supermirror.branchtargeter import branchtarget
from canonical.launchpad.scripts.supermirror.tests import createbranch
from canonical.launchpad.scripts.supermirror import jobmanager


class TestJobManager(unittest.TestCase):

    testdir = None

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        self.masterlock = os.path.join(self.testdir, 'master.lock')

    def tearDown(self):
        shutil.rmtree(self.testdir)

    def _getBranchDir(self, branchname):
        return os.path.join(self.testdir, branchname)

    def testExistance(self):
        from canonical.launchpad.scripts.supermirror.jobmanager import (
            JobManager)

    def testNotHandledObjected(self):
        """Make sure jobmanager does the right thing when it gets told that 
        there is no missing branch
        """
        manager = jobmanager.JobManager()
        manager.run()

    def testAddJobManager(self):
        manager = jobmanager.JobManager()
        brancha = self._makeBranch("brancha", None)
        manager.add(brancha)
        branchb = self._makeBranch("branchb", None)
        manager.add(branchb)
        self.assertEqual(manager.jobswaiting, 2)

    def assertEquivilantMirror(self, branch):
        mirror = BZR_5_6(branch.dest, None)
        self.assertEqual(branch, mirror) 

    def testJobRunner(self):
        manager = jobmanager.JobManager()
        self.assertEqual(manager.jobswaiting, 0)

        brancha = self._makeBranch("brancha", 0)
        manager.add(brancha)

        branchb = self._makeBranch("branchb", 11)
        manager.add(branchb)

        branchc = self._makeBranch("branchc", 222)
        manager.add(branchc)

        branchd = self._makeBranch("branchd", 333)
        manager.add(branchd)

        branche = self._makeBranch("branche", 4444)
        manager.add(branche)

        self.assertEqual(manager.jobswaiting, 5)

        manager.run()

        self.assertEqual(manager.jobswaiting, 0)
        self.assertEquivilantMirror(brancha)
        self.assertEquivilantMirror(branchb)
        self.assertEquivilantMirror(branchc)
        self.assertEquivilantMirror(branchd)
        self.assertEquivilantMirror(branche)

    def testInstallsKillHandler(self):
        controller = jobmanager.JobManagerController()

        self.assertDefaultHandler(controller)
        manager = jobmanager.JobManager()
        self.assertDefaultHandler(controller)

        manager.install() 
        try:
            newSigHandler = signal.getsignal(controller.killSignal)
            self.assertEqual(newSigHandler, manager.killRecieved)
        finally:
            manager.uninstall() 

        self.assertDefaultHandler(controller)

    def assertDefaultHandler(self, controller):
        """Ensures that the default signal handler is installed."""
        currentSigHandler = signal.getsignal(controller.killSignal)
        self.assertEqual(currentSigHandler, signal.SIG_DFL)

    def testKillRecievedInactive(self):
        manager = jobmanager.JobManager()
        manager.install()
        try:
            self.assertRaises(
                NotImplementedError, manager.killRecieved, None, None)
        finally:
            manager.uninstall()

    def testManagerCreatesLocks(self):
        try:
            manager = jobmanager.JobManager()
            self._removeLockFile()
            manager.lock(lockfilename=self.masterlock)
            self.failUnless(os.path.exists(self.masterlock))
            manager.unlock()
        finally:
            self._removeLockFile()

    def testManagerEnforcesLocks(self):
        try:
            manager = jobmanager.JobManager()
            self._removeLockFile()
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

    def _makeBranch(self, relativedir, target):
        """Given a relative directory, make a strawman branch and return it.

        @param relativedir - The directory to make the branch
        @output BZR_5_6 - A branch object representing the strawman branch
        """
        branchdir = os.path.join(self.testdir, relativedir)
        createbranch(branchdir)
        if target == None:
            targetdir = None
        else:
            targetdir = os.path.join(self.testdir, branchtarget(target))
        return BZR_5_6(branchdir, targetdir)

    def _makeAndMirrorBranch(self, relativedir, target):
        """Given a relative directory, makes a strawman branch, mirrors it
        and returns the branch object

        @param relativedir - The directory relative to cwd to make the branch
        @output BZR_5_6 - A branch object representing the strawman branch
        """
        branch = self._makeBranch(relativedir, target=target)
        branch.mirror()
        return branch


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
