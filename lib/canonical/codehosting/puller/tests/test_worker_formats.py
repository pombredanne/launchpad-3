# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the puller's support for various Bazaar formats."""

__metaclass__ = type

import unittest

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDirFormat6, BzrDirMetaFormat1
from bzrlib.repofmt.knitrepo import RepositoryFormatKnit1
from bzrlib.repofmt.weaverepo import RepositoryFormat6, RepositoryFormat7
from bzrlib.tests.repository_implementations.test_repository import (
            TestCaseWithRepository)

from canonical.codehosting.puller.tests import PullerWorkerMixin
from canonical.testing import reset_logging


class TestPullerWorkerFormats(TestCaseWithRepository, PullerWorkerMixin):

    def setUp(self):
        TestCaseWithRepository.setUp(self)
        # make_bzrdir relies on this being a relative filesystem path.
        self._source_branch_path = 'source-branch'
        self.worker = self.makePullerWorker(
            self.get_transport(self._source_branch_path).base)

    def tearDown(self):
        TestCaseWithRepository.tearDown(self)
        reset_logging()

    def _createSourceBranch(self, repository_format, bzrdir_format):
        """Make a source branch with the given formats."""
        bd = self.make_bzrdir(self._source_branch_path, format=bzrdir_format)
        repository_format.initialize(bd)
        branch = bd.create_branch()
        tree = branch.create_checkout('source-checkout')
        tree.commit('Commit message')
        self.get_transport().delete_tree('source-checkout')
        return branch

    def assertMirrored(self, source_branch, dest_branch):
        """Assert that `dest_branch` is a mirror of `src_branch`."""
        self.assertEqual(
            source_branch.last_revision(), dest_branch.last_revision())
        # Assert that the mirrored branch is in source's format
        # XXX AndrewBennetts 2006-05-18: comparing format objects is ugly.
        # See bug 45277.
        self.assertEqual(
            source_branch.repository._format.get_format_description(),
            dest_branch.repository._format.get_format_description())
        self.assertEqual(
            source_branch.bzrdir._format.get_format_description(),
            dest_branch.bzrdir._format.get_format_description())

    def _testMirrorWithFormats(self, repository_format, bzrdir_format):
        """Make a branch with certain formats, mirror it and check the mirror.

        :param repository_format: The repository format.
        :param bzrdir_format: The bzrdir format.
        """
        src_branch = self._createSourceBranch(
            repository_format, bzrdir_format)
        self.worker.mirror()
        dest_branch = Branch.open(self.worker.dest)
        self.assertMirrored(src_branch, dest_branch)

    # XXX: JonathanLange 2008-06-25: These next three tests should be
    # implemented against all supported repository formats using bzrlib's test
    # adaptation APIs. Unfortunately, this API changes between 1.5 and 1.6, so
    # it'd be a bit silly to do the work now.
    def testMirrorKnitAsKnit(self):
        # Create a source branch in knit format, and check that the mirror is
        # in knit format.
        self._testMirrorWithFormats(RepositoryFormatKnit1(), BzrDirMetaFormat1())

    def testMirrorMetaweaveAsMetaweave(self):
        # Create a source branch in metaweave format, and check that the
        # mirror is in metaweave format.
        self._testMirrorWithFormats(RepositoryFormat7(), BzrDirMetaFormat1())

    def testMirrorWeaveAsWeave(self):
        # Create a source branch in weave format, and check that the mirror is
        # in weave format.
        self._testMirrorWithFormats(RepositoryFormat6(), BzrDirFormat6())

    def testSourceFormatChange(self):
        # If a branch that has already been mirrored changes format, then we
        # when we re-mirror the branch, the mirror will acquire the new
        # format.

        # Create and mirror a branch in weave format.
        self._createSourceBranch(RepositoryFormat7(), BzrDirMetaFormat1())
        self.worker.mirror()

        # Change the branch to knit format and mirror again.
        self.get_transport().delete_tree(self._source_branch_path)
        self._createSourceBranch(RepositoryFormatKnit1(), BzrDirMetaFormat1())
        self.worker.mirror()

        # The mirrored branch should now be in knit format.
        self.assertMirrored(
            Branch.open(self.worker.source), Branch.open(self.worker.dest))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
