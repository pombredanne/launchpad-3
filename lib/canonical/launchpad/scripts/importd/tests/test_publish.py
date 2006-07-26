# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test cases for canonical.launchpad.scripts.importd.publish."""

__metaclass__ = type

__all__ = ['test_suite']


import logging
import shutil
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.branch import Branch
from bzrlib.errors import DivergedBranches

from canonical.launchpad.scripts.importd.publish import ImportdPublisher
from canonical.launchpad.scripts.importd.tests.helpers import (
    ImportdTestCase)

class TestImportdPublisher(ImportdTestCase):
    """Test canonical.launchpad.scripts.importd.publish.ImportdPublisher."""

    def setUp(self):
        ImportdTestCase.setUp(self)
        self.importd_publisher = ImportdPublisher(
            logging, self.sandbox.path, self.series_id, self.bzrmirrors)

    def assertGoodMirror(self, branch_id):
        """Helper to check that the mirror branch matches expectations."""
        # the productseries.branch.id allows us to find the mirror branch
        mirror_path = self.mirrorPath(branch_id)
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
        # branch attribute of the productseries, and pushes to a branch without
        # working tree, with a name based on the branch id.
        self.setUpOneCommit()
        self.assertEqual(self.series_helper.getSeries().branch, None)
        self.importd_publisher.publish()
        # mirrorBranch sets the series.branch in a subprocess
        db_branch = self.series_helper.getSeries().branch
        self.assertNotEqual(db_branch, None)
        self.assertGoodMirror(db_branch.id)

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
