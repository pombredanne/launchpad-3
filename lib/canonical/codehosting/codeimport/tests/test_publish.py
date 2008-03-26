# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test cases for canonical.codehosting.codeimport.publish."""

__metaclass__ = type

__all__ = ['test_suite']


import logging
import shutil
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.branch import Branch
from bzrlib.errors import DivergedBranches
from bzrlib.urlutils import local_path_to_url

from canonical.codehosting.codeimport.publish import ImportdPublisher
from canonical.codehosting.codeimport.tests.helpers import ImportdTestCase


class TestImportdPublisher(ImportdTestCase):
    """Test canonical.codehosting.codeimport.publish.ImportdPublisher."""

    def setUp(self):
        ImportdTestCase.setUp(self)
        self.importd_publisher = ImportdPublisher(
            logging, self.sandbox.path, self.series_id,
            local_path_to_url(self.bzrmirrors))

    def assertGoodMirror(self):
        """Helper to check that the mirror branch matches expectations."""
        # the productseries.import_branch.id allows us to find the
        # mirror branch
        mirror_path = self.mirrorPath()
        mirror_control = BzrDir.open(mirror_path)
        # that branch must not have a working tree
        self.assertFalse(mirror_control.has_workingtree())
        # and its history must be the same as the branch it mirrors
        mirror_branch = mirror_control.open_branch()
        mirror_history = mirror_branch.revision_history()
        bzrworking_branch = Branch.open(self.bzrworking)
        bzrworking_history = bzrworking_branch.revision_history()
        self.assertEqual(mirror_history, bzrworking_history)

    def testInitialPublish(self):
        # Initial publishing of a vcs-import creates a Branch record, sets the
        # branch attribute of the productseries, and pushes to a branch
        # without working tree, with a name based on the branch id.
        self.setUpOneCommit()
        self.assertEqual(self.series_helper.getSeries().import_branch, None)
        self.importd_publisher.publish()
        db_branch = self.series_helper.getSeries().import_branch
        self.assertNotEqual(db_branch, None)
        self.assertGoodMirror()

    def testDivergence(self):
        # Publishing a vcs-imports branch fails if there is a divergence
        # between the local branch and the mirror.
        self.setUpOneCommit()
        # publish the branch to create the mirror and modify the productseries
        # to point to a branch
        self.importd_publisher.publish()
        # create a new bzrworking branch that diverges from the mirror
        shutil.rmtree(self.bzrworking)
        self.setUpOneCommit()
        # publish now fails
        self.assertRaises(DivergedBranches, self.importd_publisher.publish)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
