import os
import shutil
import tempfile
import unittest

from canonical.launchpad.scripts.supermirror.tests import createbranch
from canonical.launchpad.scripts.supermirror.genericbranch import GenericBranch


class TestGenericBranch(unittest.TestCase):

    testdir = None

    def setUp(self):
        self.testdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.testdir)

    def _getBranchDir(self, branchname):
        return os.path.join(self.testdir, branchname)

    def testSupportedHandlesNonexistant(self):
        branch = GenericBranch()
        branch.supportsFormat("/tmp/nonexistant-huge-file-name")

    def testNegativeDetection(self):
        branchdir = self._getBranchDir("genbranch-neg-id")
        createbranch(branchdir)
        mybranch = GenericBranch(branchdir, None)
        # GenericBranch doesn't understand any branch-format file, apart from 
        # the one containing 'Generic Branch format', which is obviously not
        # created by bzr.
        self.assertFalse(mybranch.supportsFormat())

    def testPositiveDetection(self):
        branchdir = self._getBranchDir("genbranch-pos-id")
        createbranch(branchdir)
        handle = open(os.path.join(branchdir, ".bzr/branch-format"), "w")
        # This is the only branch-format file that GenericBranch understands.
        handle.write("Generic Branch format\n")
        handle.close()
        mybranch = GenericBranch(branchdir, None)
        self.assertTrue(mybranch.supportsFormat())

    def testNoLockfile(self):
        branchdir = self._getBranchDir("genbranch-lock")
        tbranchdir = self._getBranchDir("genbranch-lock-targ")
        createbranch(branchdir)
        mybranch = GenericBranch(branchdir, tbranchdir)

    def testNoEquivilance(self):
        branch = "/nonexistantlocation"
        branchA = GenericBranch(branch, None)
        branchB = GenericBranch(branch, None)
        # XXX: WTF is this test for?
        try:
            self.assertNotEquals(branchA, branchB)
        except NotImplementedError:
            pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
