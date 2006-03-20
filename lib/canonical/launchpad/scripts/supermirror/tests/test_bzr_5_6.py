import os
import shutil
import tempfile
import unittest
from StringIO import StringIO

import bzrlib.branch
from bzrlib.tests import TestCaseInTempDir
from bzrlib.weave import Weave

from canonical.launchpad.scripts.supermirror.tests import createbranch
from canonical.launchpad.scripts.supermirror.bzr_5_6 import BZR_5_6
from canonical.launchpad.scripts.supermirror.branchfactory import BranchFactory


class TestBZR_5_6(unittest.TestCase):

    testdir = None

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        # Change the HOME environment variable in order to ignore existing
        # user config files.
        os.environ.update({'HOME': self.testdir})

    def tearDown(self):
        shutil.rmtree(self.testdir)

    def _getBranchDir(self, branchname):
        return os.path.join(self.testdir, branchname)

    def testPositiveDetection(self):
        branchdir = self._getBranchDir("bzr56-negative")
        createbranch(branchdir)
        mybranch = BZR_5_6(branchdir, None)
        self.failUnless(mybranch.supportsFormat() is True)

    def testNegativeDetection(self):
        branchdir = self._getBranchDir("bzr56-positive")
        createbranch(branchdir)
        handle = open(os.path.join(branchdir, ".bzr/branch-format"), "w")
        handle.write("A non existant detection file\n")
        handle.close()
        mybranch = BZR_5_6(branchdir, None)
        self.failUnless(mybranch.supportsFormat() is False)

    def testMirror(self):
        # Create a branch
        srcbranchdir = self._getBranchDir("bzr_5_6-testmirror-src")
        destbranchdir = self._getBranchDir("bzr_5_6-testmirror-dest")

        branchfactory = BranchFactory()
        branch_56 = branchfactory.produce(
            srcbranchdir, destbranchdir, type="bzr_5_6")

        createbranch(srcbranchdir)
        branch_56.mirror()

        branch_56_mirror = branchfactory.produce(branch_56.dest)
        self.assertEqual(branch_56_mirror, branch_56)


class TestBZR_5_6_SourceProblems(TestCaseInTempDir):

    def testMissingSourceWhines(self):
        non_existant_branch = "/nonsensedir"
        mybranch = BZR_5_6(non_existant_branch, "/anothernonsensedir")
        stderr = StringIO()
        result = self.apply_redirected(None, None, stderr, mybranch.mirror)
        # result has return code
        self.assertEqual(stderr.getvalue(), "%s is unreachable\n" \
                % (non_existant_branch))

    def testMissingRevision(self):
        self.build_tree(['bzr56-missingrevision/',
                         'bzr56-missingrevision/afile'])
        branch = bzrlib.branch.Branch.initialize('bzr56-missingrevision')
        branch.working_tree().add(['afile'], ['myid'])
        branch.working_tree().commit('start')
        # now we have a good branch with a file called afile and id myid
        # we need to figure out the actual path for the weave.. or 
        # deliberately corrupt it. like this.
        branch.repository.weave_store.put_weave(
            "myid", Weave(weave_name="myid"), branch.get_transaction())

    def tearDown(self):
        TestCaseInTempDir.tearDown(self)
        test_root = TestCaseInTempDir.TEST_ROOT
        if test_root is not None and os.path.exists(test_root):
            shutil.rmtree(test_root) 
        # Set the TEST_ROOT back to None, to tell TestCaseInTempDir we need it
        # to create a new root when the next test is run.
        TestCaseInTempDir.TEST_ROOT = None


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
