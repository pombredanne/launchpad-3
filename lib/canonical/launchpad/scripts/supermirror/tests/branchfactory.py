import unittest
import os
import testlib
from supermirror.branchfactory import BranchFactory


class TestConfig(unittest.TestCase):

    def testBranchFactory(self):
        branch = os.path.join(os.getcwd(), "testdir/bchfact-pos-bzr_5_6")
        testlib.createbranch(branch)
        branchfactory = BranchFactory()
        mybranch = branchfactory.produce(branch)
        if mybranch.branchtype != "bzr_5_6":
            raise RuntimeError

    def testBranchFactoryNegative(self):
        branch = os.path.join(os.getcwd(),"testdir/bchfact-neg")
        testlib.createbranch(branch)
        handle = open (os.path.join (branch, ".bzr/branch-format"), "w")
        handle.write("A non existant detection file\n")
        handle.close()
        branchfactory = BranchFactory()
        mybranch = branchfactory.produce(branch)
        if mybranch != None:
            raise RuntimeError

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
