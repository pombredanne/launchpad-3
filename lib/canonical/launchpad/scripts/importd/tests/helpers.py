# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helpers for canonical.launchpad.scripts.importd tests."""

__metaclass__ = type

__all__ = ['ImportdTestCase']


import os
import unittest

from bzrlib.bzrdir import BzrDir

from canonical.config import config
from canonical.functional import ZopelessLayer
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from importd.tests.helpers import SandboxHelper
from importd.tests.test_bzrmanager import ProductSeriesHelper


class ImportdTestCase(unittest.TestCase):
    """Common base for test cases of importd script backends."""

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

    def tearDown(self):
        self.series_helper.tearDown()
        self.sandbox.tearDown()
        self.zopeless_helper.tearDown()

    def setUpOneCommit(self):
        workingtree = BzrDir.create_standalone_workingtree(self.bzrworking)
        workingtree.commit('first commit')

    def mirrorPath(self):
        series = self.series_helper.getSeries()
        assert series.branch is not None
        branch_id = series.branch.id
        return os.path.join(self.bzrmirrors, '%08x' % branch_id)
