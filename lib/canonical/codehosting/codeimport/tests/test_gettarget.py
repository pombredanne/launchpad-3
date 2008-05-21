# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test cases for canonical.codehosting.codeimport.gettarget."""

__metaclass__ = type

__all__ = ['test_suite']


import logging
import os
import shutil
import unittest

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.repository import Repository
from bzrlib.urlutils import local_path_to_url

from canonical.codehosting.codeimport.gettarget import ImportdTargetGetter
from canonical.codehosting.codeimport.publish import ImportdPublisher
from canonical.codehosting.codeimport.tests.helpers import (
    ImportdTestCase)


class ImportdTargetGetterTestCase(ImportdTestCase):
    """Common base for ImportTargetGetter test cases."""

    def setUp(self):
        ImportdTestCase.setUp(self)
        self.importd_publisher = ImportdPublisher(
            logging, self.sandbox.path, self.series_id,
            local_path_to_url(self.bzrmirrors))
        self.importd_getter = ImportdTargetGetter(
            logging, self.sandbox.path, self.series_id,
            local_path_to_url(self.bzrmirrors))

    def setUpMirror(self):
        self.setUpOneCommit()
        self.importd_publisher.publish()
        shutil.rmtree(self.bzrworking)

    def assertGoodBzrWorking(self):
        """Helper to check that the retrieved bzrworking matches expectations.
        """
        # Check that bzrworking is a standalone working tree.
        control = BzrDir.open(self.bzrworking)
        # We really want to use BzrDir.open_repository() to ensure this is a
        # standalone working tree.
        repository = control.open_repository()
        branch = control.open_branch()
        workingtree = control.open_workingtree()
        # Check that bzrworking has the same history as the mirror, and that
        # it is one revision long, as provided by setUpMirror.
        bzrworking_history = self.bzrworkingHistory()
        mirror_history = self.mirrorHistory()
        self.assertEqual(len(mirror_history), 1)
        self.assertEqual(bzrworking_history, mirror_history)

    def bzrworkingHistory(self):
        """Return the revision history of the bzrworking branch."""
        branch = Branch.open(self.bzrworking)
        return branch.revision_history()

    def mirrorHistory(self):
        """Return the revision history of the published mirror."""
        mirror_branch = Branch.open(self.mirrorPath())
        return mirror_branch.revision_history()


class TestImportdTargetGetter(ImportdTargetGetterTestCase):
    """Test general functionality of ImportdTargetGetter."""

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
        # That should give us a bzrworking and a mirror with different
        # histories.
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
        open(os.path.join(self.bzrworking, 'hello'), 'w').close()
        # Finally, check that get_target() can still make a good bzrworking.
        self.importd_getter.get_target()
        self.assertGoodBzrWorking()


class TestImportdTargetGetterUpgrade(ImportdTargetGetterTestCase):
    """Test upgrade functionality of ImportdTargetGetter."""

    def setUpMirror(self):
        self.setUpOneCommit(format='weave')
        self.importd_publisher.publish()
        # The publisher will creates a branch using the default format, so we
        # need to copy our old-format branch in place.
        shutil.rmtree(self.mirrorPath())
        os.rename(self.bzrworking, self.mirrorPath())
        assert self.locationNeedsUpgrade(self.mirrorPath())

    def locationNeedsUpgrade(self, location):
        """Does the branch at the provided location need a format upgrade?"""
        control = BzrDir.open_unsupported(location)
        return control.needs_format_conversion()

    def testUpgrade(self):
        # Getting a sync target upgrades the branch where possible.
        self.setUpMirror()
        # The test fixture must set up a mirror branch that needs an upgrade.
        mirror_bzrdir = BzrDir.open_unsupported(self.mirrorPath())
        self.assertTrue(self.locationNeedsUpgrade(self.mirrorPath()))
        # Get a sync target and check that it's good in the same way as in
        # testGetTarget.
        self.importd_getter.get_target()
        # That check is a bit redundant with testGetTarget, but we want to be
        # sure that the history is not lost during the upgrade.
        self.assertGoodBzrWorking()
        # Finally, check that neither the bzrworking nor the mirror need an
        # upgrade anymore.
        self.assertFalse(self.locationNeedsUpgrade(self.mirrorPath()))
        self.assertFalse(self.locationNeedsUpgrade(self.bzrworking))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


