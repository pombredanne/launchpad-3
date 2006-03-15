import unittest
import jobmanager
import signal
import os
from StringIO import StringIO
from supermirror.bzr_5_6 import BZR_5_6
from configuration import config
from branchtargeter import branchtarget
from supermirror.tests import testlib


class TestJobManager(unittest.TestCase):
    def testExistance(self):
        from jobmanager import JobManager


    def testEmptyBranchStreamToBranchList(self):
        falsestdin = StringIO("")
        manager = jobmanager.JobManager()
        self.assertEqual([], manager.branchStreamToBranchList(falsestdin))

    def testSingleBranchStreamToBranchList(self):
        """
        Get a list of branches and ensure that it can add a branch object.
        Doesn't test 
        """
        config.branchesdest = os.path.join(os.getcwd(),
                                           "testdir",
                                           "jobmanager",
                                           "singlebranchstream")
        bzr56branch = self._makeAndMirrorBranch("managersingle", 0)

        falsestdin = StringIO("0 %s\n" % (bzr56branch.source))
        manager = jobmanager.JobManager()
        branches = manager.branchStreamToBranchList(falsestdin)
        # this is better because it ensures the entire output is the same.
        self.assertEqual([bzr56branch], branches) 

    def testNotHandledObjected(self):
        """
        Make sure jobmanager does the right thing when it gets told that 
        there is no missing branch
        """
        falsestdin = StringIO("0 /nonexistantdir\n"
                              "34 /anothernondir\n")
        manager = jobmanager.JobManager()
        branches = manager.branchStreamToBranchList(falsestdin)
        for abranch in branches:
            manager.add(abranch)
        manager.run()


    def testMultiBranchStreamToBranchList(self):
        """
        Get a list of branches and ensure that it can add a branch object.
        Doesn't test 
        """
        brancha = self._makeAndMirrorBranch("managermulti1", 0)
        branchb = self._makeAndMirrorBranch("managermulti2", 314768)
        falsestdin = StringIO("0 %s\n" 
                              "314768 %s"
                              % (brancha.source, branchb.source))
        manager = jobmanager.JobManager()
        branches = manager.branchStreamToBranchList(falsestdin)
        # FIXME: Wrote this before I thought it through. Yet it PASSES??
        self.assertEqual([brancha, branchb], branches) 

    def testAddJobManager(self):
        config.branchesdest = os.path.join(os.getcwd(),
                                           "testdir",
                                           "jobmanager",
                                           "jobadder")
        manager = jobmanager.JobManager()
        brancha = self._makeBranch("brancha",None)
        manager.add(brancha)
        branchb = self._makeBranch("branchb",None)
        manager.add(branchb)
        self.assertEqual(manager.jobswaiting, 2)

    def assertEquivilantMirror(self,branch):
        mirror = BZR_5_6(branch.dest, None)
        self.assertEqual(branch, mirror) 

    def testJobRunner(self):
        config.branchesdest = os.path.join(os.getcwd(),
                                           "testdir",
                                           "jobmanager",
                                           "jobrunner")
        manager = jobmanager.JobManager()
        self.assertEqual(manager.jobswaiting, 0)

        brancha = self._makeBranch("brancha",0)
        manager.add(brancha)

        branchb = self._makeBranch("branchb",11)
        manager.add(branchb)

        branchc = self._makeBranch("branchc",222)
        manager.add(branchc)

        branchd = self._makeBranch("branchd",333)
        manager.add(branchd)

        branche = self._makeBranch("branche",4444)
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
        """
        Ensures that the default signal handler is installed
        """
        currentSigHandler = signal.getsignal(controller.killSignal)
        self.assertEqual(currentSigHandler, signal.SIG_DFL)


    def testKillRecievedInactive(self):
        manager = jobmanager.JobManager()
        manager.install()
        try:
            self.assertRaises(NotImplementedError, manager.killRecieved, 
                              None, None)
        finally:
            manager.uninstall()


    def testManagerCreatesLocks(self):
        self._setupManagerLock()
        try:
            manager = jobmanager.JobManager()
            if os.path.exists(self.mylockfile):
                os.unlink(self.mylockfile)
            manager.lock()
            self.failUnless(os.path.exists(self.mylockfile))
            manager.unlock()
        finally:
            config.masterlock = self.oldlock
            self._removeLockFile()


    def testManagerEnforcesLocks(self):
        self._setupManagerLock()
        try:
            manager = jobmanager.JobManager()
            if os.path.exists(self.mylockfile):
                os.unlink(self.mylockfile)
            manager.lock()
            anothermanager = jobmanager.JobManager()
            self.assertRaises(jobmanager.LockError, anothermanager.lock)
            self.failUnless(os.path.exists(self.mylockfile))
            manager.unlock()
        finally:
            config.masterlock = self.oldlock
            self._removeLockFile()


    def _removeLockFile(self):
        if os.path.exists(self.mylockfile):
            os.unlink(self.mylockfile)


    def _setupManagerLock(self):
        self.oldlock = config.masterlock
        self.mylockfile = os.path.join(os.getcwd(), 'lockfile')
        config.masterlock=self.mylockfile

    def _makeBranch(self, relativedir, target):
        """
        Given a relative directory, makes a strawman branch, mirrors it
        and returns the branch object

        @param relativedir - The directory relative to cwd to make the branch
        @output BZR_5_6 - A branch object representing the strawman branch
        """

        branchdir = os.path.join(config.branchesdest,relativedir)
        testlib.createbranch(branchdir)
        if target==None:
            targetdir = None
        else:
            targetdir = config.branchesdest + branchtarget(target)
        return BZR_5_6(branchdir, targetdir)

    def _makeAndMirrorBranch(self, relativedir, target):
        """
        Given a relative directory, makes a strawman branch, mirrors it
        and returns the branch object

        @param relativedir - The directory relative to cwd to make the branch
        @output BZR_5_6 - A branch object representing the strawman branch
        """

        branch = self._makeBranch(relativedir, target=target)
        branch.mirror()
        return branch


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
