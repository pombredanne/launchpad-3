import unittest
import os
from StringIO import StringIO

import bzrlib.branch
import bzrlib.bzrdir
import bzrlib.tests
import bzrlib.store.versioned
import bzrlib.transport

import testlib
from supermirror.bzr_5_6 import BZR_5_6
from configuration import config
from supermirror.branchfactory import BranchFactory

class TestBZR_5_6(unittest.TestCase):

    def testPositiveDetection(self):
        bn = "testdir/bzr56-negative"
        branchdir = os.getcwd() + os.sep + bn
        testlib.createbranch(bn)
        mybranch = BZR_5_6(branchdir, None)
        if mybranch.supportsFormat() is not True:
            raise RuntimeError

    def testNegativeDetection(self):
        bn = "testdir/bzr56-positive"
        branchdir = os.path.join(os.getcwd(),bn)
        testlib.createbranch(bn)
        handle = open (os.path.join (branchdir, ".bzr/branch-format"), "w")
        handle.write("A non existant detection file\n")
        handle.close()
        mybranch = BZR_5_6(branchdir, None)
        if mybranch.supportsFormat() is not False:
            raise RuntimeError

    def testMirror(self):

        # Create a branch
        config.branchesdest = os.path.join(os.getcwd(), "testdir", "branches")
        bsource = os.path.join(config.branchesdest, "bzr_5_6-testmirror-src")
        bdest = os.path.join(config.branchesdest, "bzr_5_6-testmirror-dest")

        # Should be a test case.
        branchfact = BranchFactory()
        branch_56 = branchfact.produce(bsource, bdest, type="bzr_5_6", )

        testlib.createbranch(bsource)
        branch_56.mirror()

        branch_56_mirror = branchfact.produce(branch_56.dest)
        self.assertEqual(branch_56_mirror, branch_56)


class TestBZR_5_6_SourceProblems(bzrlib.tests.TestCaseInTempDir):

    def testMissingSourceWhines(self):
        non_existant_branch = "/nonsensedir"
        mybranch = BZR_5_6(non_existant_branch, "/anothernonsensedir")
        stderr = StringIO()
        result = self.apply_redirected(None, None, stderr, mybranch.mirror)
        # result has return code
        self.assertEqual(stderr.getvalue(), "%s is unreachable\n" \
                % (non_existant_branch))

    def testMissingRevision(self):
        self.build_tree(['testdir/', 'testdir/bzr56-missingrevision/',
                         'testdir/bzr56-missingrevision/afile'])
        #branch = bzrlib.branch.Branch.initialize(
        #    'testdir/bzr56-missingrevision')
        wt = bzrlib.bzrdir.BzrDir.create_standalone_workingtree('testdir/bzr56-missingrevision')
        wt.add(['afile'], ['myid'])
        repo = wt.branch.repository
        # now we have a good branch with a file called afile and id myid
        # we need to figure out the actual path for the weave.. or 
        # deliberately corrupt it. like this.
        # Delete existing storage for this file and replace with empty
        # weave.
        repo.weave_store.get_empty('myid', repo.get_transaction())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
