import unittest
import os
import testlib
from supermirror.genericbranch import GenericBranch

class TestConfig(unittest.TestCase):

    def testSupportedHandlesNonexistant(self):
        branch = GenericBranch()
        branch.supportsFormat("/nonexistant")


    def testNegativeDetection(self):
        from supermirror.genericbranch import GenericBranch
        branch = os.path.join(os.getcwd(), "testdir/genbranch-neg-id")
        testlib.createbranch(branch)
        mybranch = GenericBranch(branch, None)
        if mybranch.supportsFormat() is not False:
            raise RuntimeError

    def testPositiveDetection(self):
        from supermirror.genericbranch import GenericBranch
        branch = os.path.join(os.getcwd(),"testdir/genbranch-pos-id")
        testlib.createbranch(branch)
        handle = open (os.path.join (branch, ".bzr/branch-format"), "w")
        handle.write("A non existant detection file\n")
        handle.close()

        mybranch = GenericBranch(branch, None)
        if mybranch.supportsFormat() is not True:
            raise RuntimeError

    def testNoLockfile(self):
        from supermirror.genericbranch import GenericBranch
        branch = os.path.join(os.getcwd(),"testdir/genbranch-lock")
        tbranch = os.path.join(os.getcwd(),"testdir/genbranch-lock-targ")
        testlib.createbranch(branch)
        mybranch = GenericBranch(branch, tbranch)

    def testNoEquivilance(self):
        branch = "/nonexistantlocation"
        branchA = GenericBranch(branch, None)
        branchB = GenericBranch(branch, None)
        try:
            self.assertNotEquals(branchA, branchB)
        except NotImplementedError:
            pass

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
