# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test cases for canonical.launchpad.scripts.importd.publish."""

__metaclass__ = type

__all__ = ['test_suite']


import logging
import os
import shutil
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.branch import Branch
from bzrlib.errors import DivergedBranches
from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import rollback, commit
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.launchpad.interfaces import ILaunchpadCelebrities, IBranchSet
from canonical.launchpad.scripts.importd.publish import ImportdPublisher
from canonical.testing import ZopelessLayer
from importd.tests.helpers import SandboxHelper
from importd.tests.test_bzrmanager import ProductSeriesHelper

class TestImportdPublisher(unittest.TestCase):
    """Test canonical.launchpad.scripts.importd.publish.ImportdPublisher."""

    layer = ZopelessLayer

    def setUp(self):
        self.zopeless_helper = LaunchpadZopelessTestSetup(
            dbuser=config.importd.dbuser)
        self.zopeless_helper.setUp()
        self.sandbox = SandboxHelper()
        self.sandbox.setUp()
        self.bzrworking = self.sandbox.join('bzrworking')
        self.bzrmirrors = self.sandbox.join('bzr-mirrors')
        os.mkdir(self.bzrmirrors)
        self.series_helper = ProductSeriesHelper()
        self.series_helper.setUp()
        self.series_helper.setUpSeries()
        self.series_id = self.series_helper.series.id
        self.importd_publisher = ImportdPublisher(
            logging, self.sandbox.path, self.series_id, self.bzrmirrors)

    def tearDown(self):
        self.series_helper.tearDown()
        self.sandbox.tearDown()
        self.zopeless_helper.tearDown()

    def setUpOneCommit(self):
        workingtree = BzrDir.create_standalone_workingtree(self.bzrworking)
        workingtree.commit('first commit')

    def checkMirror(self, branch_id):
        """Helper to check that the mirror branch matches expectations."""
        # the productseries.branch.id allows us to find the mirror branch
        mirror_path = os.path.join(self.bzrmirrors, '%08x' % branch_id)
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
        db_branch = self.series_helper.getSeries().branch
        self.assertNotEqual(db_branch, None)
        self.checkMirror(db_branch.id)

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

    def testBadBranchOwner(self):
        # Publishing an import fails if there is a branch associated with the
        # ProductSeries and its owner is not 'vcs-imports'.
        self.setUpOneCommit()
        series = self.series_helper.series
        branch = getUtility(IBranchSet).new(
            series.name, series.product.owner, series.product, url=None)
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        assert branch.owner != vcs_imports
        series.branch = branch
        commit()
        self.assertRaises(AssertionError, self.importd_publisher.publish)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
