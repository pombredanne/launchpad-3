import os
import shutil
import tempfile
import unittest
from StringIO import StringIO

import bzrlib.branch
from bzrlib.tests import TestCaseInTempDir
from bzrlib.weave import Weave

from canonical.launchpad.scripts.supermirror.tests import createbranch
from canonical.launchpad.scripts.supermirror.branchtomirror import BranchToMirror


class TestBranchToMirror(unittest.TestCase):

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

    def testMirror(self):
        # Create a branch
        srcbranchdir = self._getBranchDir("branchtomirror-testmirror-src")
        destbranchdir = self._getBranchDir("branchtomirror-testmirror-dest")

        branch_56 = BranchToMirror(srcbranchdir, destbranchdir)

        tree = createbranch(srcbranchdir)
        branch_56.mirror()
        mirrored_tree = bzrlib.workingtree.WorkingTree.open(branch_56.dest)
        self.assertEqual(tree.last_revision(), mirrored_tree.last_revision())


class TestBranchToMirror_SourceProblems(TestCaseInTempDir):

    def testMissingSourceWhines(self):
        non_existant_branch = "/nonsensedir"
        mybranch = BranchToMirror(non_existant_branch, "/anothernonsensedir")
        stderr = StringIO()
        result = self.apply_redirected(None, None, stderr, mybranch.mirror)
        # result has return code
        self.assertEqual(stderr.getvalue(), "%s is unreachable\n" \
                % (non_existant_branch))

    def testMissingFileRevisionData(self):
        self.build_tree(['bzr56-missingrevision/',
                         'bzr56-missingrevision/afile'])
        tree = bzrlib.bzrdir.BzrDir.create_standalone_workingtree(
            'bzr56-missingrevision')
        tree.add(['afile'], ['myid'])
        tree.commit('start')
        # now we have a good branch with a file called afile and id myid
        # we need to figure out the actual path for the weave.. or 
        # deliberately corrupt it. like this.
        tree.branch.repository.weave_store.put_weave(
            "myid", Weave(weave_name="myid"), 
            tree.branch.repository.get_transaction())

    def tearDown(self):
        TestCaseInTempDir.tearDown(self)
        test_root = TestCaseInTempDir.TEST_ROOT
        if test_root is not None and os.path.exists(test_root):
            shutil.rmtree(test_root) 
        # Set the TEST_ROOT back to None, to tell TestCaseInTempDir we need it
        # to create a new root when the next test is run.
        # The TestCaseInTempDir is part of bzr's test infrastructure and the
        # bzr test runner normally does this cleanup, but here we have to do
        # that ourselves.
        TestCaseInTempDir.TEST_ROOT = None


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
