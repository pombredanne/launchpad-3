import os
import shutil
import unittest

import bzrlib
from bzrlib import bzrdir
from bzrlib.tests.repository_implementations.test_repository import (
            TestCaseWithRepository)


from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.puller.tests import PullerWorkerMixin
from canonical.testing import reset_logging


class TestPullerWorkerFormats(TestCaseWithRepository, PullerWorkerMixin):

    def setUp(self):
        TestCaseWithRepository.setUp(self)

    def tearDown(self):
        TestCaseWithRepository.tearDown(self)
        reset_logging()

    def testMirrorKnitAsKnit(self):
        # Create a source branch in knit format, and check that the mirror is
        # in knit format.
        self.bzrdir_format = bzrdir.BzrDirMetaFormat1()
        self.repository_format = \
            bzrlib.repofmt.knitrepo.RepositoryFormatKnit1()
        self._testMirrorFormat()

    def testMirrorMetaweaveAsMetaweave(self):
        # Create a source branch in metaweave format, and check that the
        # mirror is in metaweave format.
        self.bzrdir_format = bzrdir.BzrDirMetaFormat1()
        self.repository_format = bzrlib.repofmt.weaverepo.RepositoryFormat7()
        self._testMirrorFormat()

    def testMirrorWeaveAsWeave(self):
        # Create a source branch in weave format, and check that the mirror is
        # in weave format.
        self.bzrdir_format = bzrdir.BzrDirFormat6()
        self.repository_format = bzrlib.repofmt.weaverepo.RepositoryFormat6()
        self._testMirrorFormat()

    def testSourceFormatChange(self):
        # Create and mirror a branch in weave format.
        self.bzrdir_format = bzrdir.BzrDirMetaFormat1()
        self.repository_format = bzrlib.repofmt.weaverepo.RepositoryFormat7()
        self._createSourceBranch()
        self._mirror()

        # Change the branch to knit format.
        shutil.rmtree('src-branch')
        self.repository_format = \
            bzrlib.repofmt.knitrepo.RepositoryFormatKnit1()
        self._createSourceBranch()

        # Mirror again.  The mirrored branch should now be in knit format.
        mirrored_branch = self._mirror()
        self.assertEqual(
            self.repository_format.get_format_description(),
            mirrored_branch.repository._format.get_format_description())

    def _createSourceBranch(self):
        ensure_base(self.get_transport('src-branch'))
        tree = self.make_branch_and_tree('src-branch')
        self.local_branch = tree.branch
        self.build_tree(['foo'], transport=self.get_transport('./src-branch'))
        tree.add('foo')
        tree.commit('Added foo', rev_id='rev1')
        return tree

    def _mirror(self):
        # Mirror src-branch to dest-branch
        source_url = os.path.abspath('src-branch')
        to_mirror = self.makePullerWorker(src_dir=source_url)
        to_mirror.mirror()
        mirrored_branch = bzrlib.branch.Branch.open(to_mirror.dest)
        return mirrored_branch

    def _testMirrorFormat(self):
        tree = self._createSourceBranch()

        mirrored_branch = self._mirror()
        self.assertEqual(tree.last_revision(),
                         mirrored_branch.last_revision())

        # Assert that the mirrored branch is in source's format
        # XXX AndrewBennetts 2006-05-18: comparing format objects is ugly.
        # See bug 45277.
        self.assertEqual(
            self.repository_format.get_format_description(),
            mirrored_branch.repository._format.get_format_description())
        self.assertEqual(
            self.bzrdir_format.get_format_description(),
            mirrored_branch.bzrdir._format.get_format_description())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
