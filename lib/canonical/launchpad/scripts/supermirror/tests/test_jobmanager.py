import os
import shutil
import tempfile
import unittest
from StringIO import StringIO

import bzrlib

from canonical.config import config
from canonical.launchpad.scripts.supermirror.branchtomirror import BranchToMirror
from canonical.launchpad.scripts.supermirror.branchtargeter import branchtarget
from canonical.launchpad.scripts.supermirror.tests import createbranch
from canonical.launchpad.scripts.supermirror import jobmanager


class TestJobManager(unittest.TestCase):

    testdir = None

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        self.masterlock = os.path.join(self.testdir, 'master.lock')
        # Change the HOME environment variable in order to ignore existing
        # user config files.
        os.environ.update({'HOME': self.testdir})

    def tearDown(self):
        shutil.rmtree(self.testdir)

    def _getBranchDir(self, branchname):
        return os.path.join(self.testdir, branchname)

    def testExistance(self):
        from canonical.launchpad.scripts.supermirror.jobmanager import (
            JobManager)
        assert JobManager

    def testEmptyBranchStreamToBranchList(self):
        falsestdin = StringIO("")
        manager = jobmanager.JobManager()
        self.assertEqual([], manager.branchStreamToBranchList(falsestdin))

    def testSingleBranchStreamToBranchList(self):
        """Get a list of branches and ensure that it can add a branch object."""
        expected_branch = BranchToMirror(
            'managersingle', config.supermirror.branchesdest + '/00/00/00/00')
        falsestdin = StringIO("0 managersingle\n")
        manager = jobmanager.JobManager()
        branches = manager.branchStreamToBranchList(falsestdin)
        self.assertEqual([expected_branch], branches) 

    def testAddJobManager(self):
        manager = jobmanager.JobManager()
        manager.add(BranchToMirror('foo', 'bar'))
        manager.add(BranchToMirror('baz', 'bar'))
        self.assertEqual(len(manager.branches_to_mirror), 2)

    def assertMirrored(self, branch):
        source_tree = bzrlib.workingtree.WorkingTree.open(branch.source)
        dest_tree = bzrlib.workingtree.WorkingTree.open(branch.dest)
        self.assertEqual(source_tree.last_revision(), dest_tree.last_revision())

    def testJobRunner(self):
        manager = jobmanager.JobManager()
        self.assertEqual(len(manager.branches_to_mirror), 0)

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

        self.assertEqual(len(manager.branches_to_mirror), 5)

        manager.run()

        self.assertEqual(len(manager.branches_to_mirror), 0)
        self.assertMirrored(brancha)
        self.assertMirrored(branchb)
        self.assertMirrored(branchc)
        self.assertMirrored(branchd)
        self.assertMirrored(branche)

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
        @output BranchToMirror - A branch object representing the strawman branch
        """
        branchdir = os.path.join(self.testdir, relativedir)
        createbranch(branchdir)
        if target == None:
            targetdir = None
        else:
            targetdir = os.path.join(self.testdir, branchtarget(target))
        return BranchToMirror(branchdir, targetdir)

    def _makeAndMirrorBranch(self, relativedir, target):
        """Given a relative directory, makes a strawman branch, mirrors it
        and returns the branch object

        @param relativedir - The directory relative to cwd to make the branch
        @output BranchToMirror - A branch object representing the strawman branch
        """
        branch = self._makeBranch(relativedir, target=target)
        branch.mirror()
        return branch


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
