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
from bzrlib.repository import Repository
from zope.component import getUtility

from canonical.database.sqlbase import commit
from canonical.launchpad.interfaces import ILaunchpadCelebrities
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
        # check that bzrworking is a standalone working tree
        control = BzrDir.open(self.bzrworking)
        # we really want to use BzrDir.open_repository() to ensure this is a
        # standalone working tree
        repository = control.open_repository()
        branch = control.open_branch()
        workingtree = control.open_workingtree()
        # check that bzrworking has the same history as the mirror
        bzrworking_history = self.bzrworkingHistory()
        mirror_history = self.mirrorHistory()
        self.assertEqual(bzrworking_history, mirror_history)

    def bzrworkingHistory(self):
        """Return the revision history of the bzrworking branch."""
        branch = Branch.open(self.bzrworking)
        return branch.revision_history()

    def mirrorHistory(self):
        """Return the revision history of the published mirror."""
        mirror_branch = Branch.open(self.mirrorPath())
        return mirror_branch.revision_history()

    def testGetTarget(self):
        # ImportdTargetGetter.get_target makes a new standalone working tree
        # based on the existing mirror.
        self.setUpMirror()
        assert not os.path.exists(self.bzrworking)
        self.importd_getter.get_target()
        self.assertGoodBzrWorking()

    def testOverwriteTarget(self):
        # ImportdTargetGetter.get_target can overwrite an existing bzr branch.
        self.setUpMirror()
        # Create a new, different, branch as bzrworking.
        self.setUpOneCommit()
        # That should have given us a bzrworking and a mirror with different
        # history.
        assert self.bzrworkingHistory() != self.mirrorHistory()
        # get_target must overwrite that existing bzrworking.
        self.importd_getter.get_target()
        self.assertGoodBzrWorking()
        # We must not only overwrite the history, but the whole branch, to
        # avoid accumulating cruft in the repository.
        bzrworking_repository = Repository.open(self.bzrworking)
        mirror_repository = Repository.open(self.mirrorPath())
        self.assertEqual(
            bzrworking_repository.all_revision_ids(),
            mirror_repository.all_revision_ids())
        # That must work as well when bzrworking is not a proper branch.
        # First delete the bzrworking branch we just created.
        shutil.rmtree(self.bzrworking)
        # Then create a directory in its place.
        os.mkdir(self.bzrworking)
        # And create a file in the directory, to ensure that get_target() does
        # a recursive delete.
        open(os.path.join(self.bzrworking, 'hello'), 'w').close
        # Finally, check that get_target() can still make a good bzrworking.
        self.importd_getter.get_target()
        self.assertGoodBzrWorking()

    def testBadBranchOwner(self):
        # Getting a sync target fails if the branch associated with the
        # ProductSeries has an owner other than vcs-imports.
        # First create the standard test mirror.
        self.setUpMirror()
        # Then set the branch owner to something other than vcs_imports, so we
        # end up with an environment that is valid for get_target in all
        # respects, except for the owner of the branch record.
        series = self.series_helper.series
        series.branch.owner = series.product.owner
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        assert series.branch.owner != vcs_imports
        commit()
        # This bad value of the branch owner must be enough to cause a failure.
        self.assertRaises(AssertionError, self.importd_getter.get_target)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


