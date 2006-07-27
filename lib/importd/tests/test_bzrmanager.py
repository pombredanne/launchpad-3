# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Tests for the bzr back-end to importd."""

__metaclass__ = type

__all__ = ['test_suite']


import os
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.branch import Branch
from zope.component import getUtility

from canonical.database.sqlbase import commit, rollback
from canonical.launchpad.interfaces import IProductSet
from importd import Job
from importd.bzrmanager import BzrManager
from importd.tests.helpers import SandboxHelper, ZopelessUtilitiesHelper


class NoopJob(object):
    """Fake job object to make BzrManager.__init__ happy.

    Used to test the no-op methods in BzrManager.
    """

    def __init__(self):
        self.logger = None
        self.seriesID = None
        self.push_prefix = None


class TestNoopMethods(unittest.TestCase):
    """Check presence of no-op methods needed for ArchiveManager compatibility.

    The methods tested in this class are not expected to do anything, but they
    must be present for compatibility with the ArchiveManager API.
    """

    def setUp(self):
        job = NoopJob()
        self.bzr_manager = BzrManager(job)

    def testCreateMaster(self):
        # BzrManager.createMaster can be called.
        self.bzr_manager.createMaster()

    def testCreateMirror(self):
        # BzrManager.createMirror can be called.
        self.bzr_manager.createMirror()

    def testNukeMaster(self):
        # BzrManager.nukeMaster can be called
        self.bzr_manager.nukeMaster()

    def testRollbackToMirror(self):
        # BzrManager.rollbackToMirror can be called
        self.bzr_manager.rollbackToMirror()


class BzrManagerJobHelper(object):
    """Job Factory for BzrManager test cases."""

    def __init__(self, sandbox):
        self.sandbox = sandbox

    def setUp(self):
        self.sandbox.mkdir('bzr-mirrors')

    def tearDown(self):
        pass

    jobType = Job.CopyJob

    def makeJob(self):
        job = self.jobType()
        job.slave_home = self.sandbox.path
        job.push_prefix = self.sandbox.join('bzr-mirrors')
        job.seriesID = None
        return job


class BzrManagerTestCase(unittest.TestCase):
    """Common base for BzrManager test cases."""

    def setUp(self):
        self.sandbox = SandboxHelper()
        self.sandbox.setUp()
        self.job_helper = BzrManagerJobHelper(self.sandbox)
        self.job_helper.setUp()
        self.job = self.makeJob()
        self.bzr_manager = BzrManager(self.job)
        self.bzrworking = self.sandbox.join('bzrworking')

    def makeJob(self):
        return self.job_helper.makeJob()

    def tearDown(self):
        self.job_helper.tearDown()
        self.sandbox.tearDown()


class TestCreateImportTarget(BzrManagerTestCase):

    def test(self):
        # BzrManager.createImportTarget creates an empty bzr standalone tree
        self.bzr_manager.createImportTarget(self.sandbox.path)
        self.assertTrue(os.path.isdir(self.bzrworking))
        # createImportTarget must create a standalone working tree
        control = BzrDir.open(self.bzrworking)
        # we really want to use BzrDir.open_repository() to ensure this is a
        # standalone working tree
        repository = control.open_repository()
        branch = control.open_branch()
        workingtree = control.open_workingtree()
        # the resulting repository must be empty
        self.assertEqual(repository.all_revision_ids(), [])
        # the branch must have no history
        self.assertEqual(branch.last_revision(), None)
        # and the working tree must be empty
        self.assertEqual(list(workingtree.list_files()), [])


class ProductSeriesHelper:
    """Helper for tests that use the testing ProductSeries."""

    def setUp(self):
        self.series = None

    def tearDown(self):
        pass

    def setUpSeries(self):
        """Create a sample ProductSeries."""
        assert self.series is None
        product = getUtility(IProductSet)['gnome-terminal']
        series = product.newSeries(product.owner, 'importd-test', summary='')
        self.series = series
        commit()

    def getSeries(self):
        """Retrieve the sample ProductSeries.

        That is useful to test that changes to the ProductSeries reached the
        database.
        """
        product = getUtility(IProductSet)['gnome-terminal']
        series = product.getSeries('importd-test')
        return series


class TestMirrorMethods(BzrManagerTestCase):
    """Test BzrManager methods that deal with the mirror branch."""

    def setUp(self):
        self.utilities_helper = ZopelessUtilitiesHelper()
        self.utilities_helper.setUp()
        self.series_helper = ProductSeriesHelper()
        self.series_helper.setUp()
        self.series_helper.setUpSeries()
        self.series_id = self.series_helper.series.id
        BzrManagerTestCase.setUp(self)
        self.saved_dbname = os.environ.get('LP_DBNAME')
        os.environ['LP_DBNAME'] = 'launchpad_ftest'

    def tearDown(self):
        if self.saved_dbname is None:
            del os.environ['LP_DBNAME']
        else:
            os.environ['LP_DBNAME'] = self.saved_dbname
        BzrManagerTestCase.tearDown(self)
        self.series_helper.tearDown()
        self.utilities_helper.tearDown()

    def makeJob(self):
        job = self.job_helper.makeJob()
        job.seriesID = self.series_id
        return job

    def setUpOneCommit(self):
        workingtree = BzrDir.create_standalone_workingtree(self.bzrworking)
        workingtree.commit('first commit')

    def testMirrorBranch(self):
        # BzrManager.mirrorBranch does something useful That is only intended
        # to test that mirrorBranch can run the importd-publish.py script. The
        # detailed tests are in
        # canonical.launchpad.scripts.importd.tests.test_publish.
        self.setUpOneCommit()
        self.assertEqual(self.series_helper.getSeries().branch, None)
        self.bzr_manager.silent = True
        self.bzr_manager.mirrorBranch(self.sandbox.path)
        # mirrorBranch sets the series.branch in a subprocess, we need to
        # rollback at this point to see this change in the database
        rollback()
        db_branch = self.series_helper.getSeries().branch
        self.assertNotEqual(db_branch, None)
        mirror_path = os.path.join(self.job.push_prefix, '%08x' % db_branch.id)
        mirror = Branch.open(mirror_path)
        self.assertEqual(mirror.revno(), 1)

    def testMirrorBranchFailure(self):
        # BzrManager.mirrorBranch raises SystemExit in case of failure.
        # To cause a failure, we abstain from creating a branch to mirror.
        self.bzr_manager.silent = True
        self.assertRaises(SystemExit,
            self.bzr_manager.mirrorBranch, self.sandbox.path)


from importd.tests import testutil
testutil.register(__name__)

