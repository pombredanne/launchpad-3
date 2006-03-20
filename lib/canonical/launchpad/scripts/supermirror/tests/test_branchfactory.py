import os
import shutil
import tempfile
import unittest

from canonical.launchpad.scripts.supermirror.tests import createbranch
from canonical.launchpad.scripts.supermirror.branchfactory import BranchFactory


class TestBranchFactory(unittest.TestCase):

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

    def testBranchFactory(self):
        branchdir = self._getBranchDir("bchfact-pos-bzr_5_6")
        createbranch(branchdir)
        mybranch = BranchFactory().produce(branchdir)
        self.failUnless(mybranch.branchtype == "bzr_5_6")

    def testBranchFactoryNegative(self):
        branchdir = self._getBranchDir("bchfact-neg")
        createbranch(branchdir)
        handle = open(os.path.join(branchdir, ".bzr/branch-format"), "w")
        handle.write("A non existant detection file\n")
        handle.close()
        mybranch = BranchFactory().produce(branchdir)
        self.failUnless(mybranch is None)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
