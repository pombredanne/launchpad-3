# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test cases for canonical.launchpad.scripts.importd.gettarget."""

__metaclass__ = type

__all__ = ['test_suite']


import logging
import os
import shutil
import unittest

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir

from canonical.launchpad.scripts.importd.gettarget import ImportdTargetGetter
from canonical.launchpad.scripts.importd.publish import ImportdPublisher
from canonical.launchpad.scripts.importd.tests.helpers import (
    ImportdTestCase)


class TestImportdTargetGetter(ImportdTestCase):
    """Test canonical.launchpad.scripts.importd.publish.ImportdTargetGetter."""

    def setUp(self):
        ImportdTestCase.setUp(self)
        self.importd_publisher = ImportdPublisher(
            logging, self.sandbox.path, self.series_id, self.bzrmirrors)
        self.importd_getter = ImportdTargetGetter(
            logging, self.sandbox.path, self.series_id, self.bzrmirrors)

    def setUpMirror(self):
        self.setUpOneCommit()
        self.importd_publisher.publish()
        shutil.rmtree(self.bzrworking)

    def assertGoodBzrWorking(self):
        """Helper to check that the retrieved bzrworking matches expectations.
        """
        series = self.series_helper.series
        # get the mirror_history to compare to the bzrworking history
        mirror_path = self.mirrorPath(series.branch.id)
        mirror_branch = Branch.open(mirror_path)
        mirror_history = mirror_branch.revision_history()
        # check that bzrworking is a standalone working tree
        control = BzrDir.open(self.bzrworking)
        # we really want to use BzrDir.open_repository() to ensure this is a
        # standalone working tree
        repository = control.open_repository()
        branch = control.open_branch()
        workingtree = control.open_workingtree()
        # check that bzrworking has the same history as the mirror
        bzrworking_history = branch.revision_history()
        self.assertEqual(bzrworking_history, mirror_history)

    def testGetTarget(self):
        # ImportdTargetGetter.get_target makes a new standalone working tree
        # based on the existing mirror.
        self.setUpMirror()
        assert not os.path.exists(self.bzrworking)
        self.importd_getter.get_target()
        self.assertGoodBzrWorking()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


