# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Tests for the bzr back-end to importd."""

__metaclass__ = type

__all__ = ['test_suite']


import os
import shutil
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.branch import Branch
from bzrlib.urlutils import local_path_to_url
from zope.component import getUtility

from canonical.database.sqlbase import commit, rollback
from canonical.launchpad.interfaces import IProductSet
from importd import Job
from importd.bzrmanager import BzrManager
from importd.tests.helpers import SandboxHelper, ZopelessUtilitiesHelper
from importd.tests.testutil import makeSilentLogger
from canonical.launchpad.scripts.importd.publish import ImportdPublisher

class NoopJob(object):
    """Fake job object to make BzrManager.__init__ happy.

    Used to test the no-op methods in BzrManager.
    """

    def __init__(self):
        self.logger = None
        self.seriesID = None
        self.push_prefix = None


class TestRunCommand(unittest.TestCase):
    """Tests for the BzrManager._runCommand utility."""

    def setUp(self):
        job = NoopJob()
        self.bzr_manager = BzrManager(job)

    def testRunCommandFailure(self):
        # BzrManager._runCommand raises SystemExit in case of failure.
        self.assertRaises(SystemExit,
            self.bzr_manager._runCommand, ['/bin/false'])


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
        job.push_prefix = local_path_to_url(self.sandbox.join('bzr-mirrors'))
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
        self.push_prefix = self.job.push_prefix
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
        # and return its path
        value = self.bzr_manager.createImportTarget(self.sandbox.path)
        self.assertEqual(value, self.bzrworking)
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
        workingtree.lock_read()
        try:
            self.assertEqual(list(workingtree.list_files()), [])
        finally:
            workingtree.unlock()


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

    def mirrorPath(self, branch_id):
        return os.path.join(self.push_prefix, '%08x' % branch_id)

    def testMirrorBranch(self):
        # The scope of this test case is to test:
        # - that mirrorBranch exists and is a method that accepts a path
        # - that when called it runs importd-publish.py
        # - that this script is called with the appropriate arguments
        # - that the script runs to completion and calls the backend at least
        #   somewhat.

        # Setup a bzrworking with some history
        self.setUpOneCommit()
        # The test ProductSeries must not have a branch yet, so we can check
        # that mirrorBranch sets the ProductSeries.import_branch.
        assert self.series_helper.getSeries().import_branch is None
        # Call mirrorBranch to set the series.import_branch and create
        # the mirror
        self.bzr_manager.mirrorBranch(self.sandbox.path)
        # mirrorBranch sets the series.import_branch in a subprocess,
        # we need to rollback at this point to see this change in the
        # database
        rollback()
        # Check that mirrorBranch has set the series.import_branch.
        db_branch = self.series_helper.getSeries().import_branch
        self.assertNotEqual(db_branch, None)
        # Use the id of the branch to locate the mirror, and check that it
        # contains some history.
        mirror_path = self.mirrorPath(db_branch.id)
        mirror = Branch.open(mirror_path)
        self.assertNotEqual(mirror.revno(), 0)

    def testGetSyncTarget(self):
        # The scope of this test case is to test:
        # - that getSyncTarget exists and is a method that accepts a path
        # - that getSyncTarget returns the right value
        # - that when called it runs importd-get-target.py
        # - that this script is called with the appropriate arguments
        # - that the script runs to completion and calls the backend at least
        #   somewhat.

        # First, set up a mirror using BzrManager.mirrorBranch
        # Set up our standard one-commit test branch.
        self.setUpOneCommit()
        # Mirror the one-commit branch, which is in the sandbox. We call
        # directly into the back-end of bzr_manager.mirrorBranch to save the
        # cost of setup_zcml_for_scripts.
        logger = makeSilentLogger()
        importd_publisher = ImportdPublisher(
            logger, self.sandbox.path, self.series_id, self.push_prefix)
        importd_publisher.publish()
        # Delete the branch we created with setUpOneCommit.  We delete this
        # so that we are definitely getting something from the mirror, and
        # not the original.
        shutil.rmtree(self.bzrworking)
        # Finally, call getSyncTarget to re-create the one-commit branch
        # in bzrworking.  We recreate it by branching the mirrored branch
        # we created just above.
        value = self.bzr_manager.getSyncTarget(self.sandbox.path)
        self.assertEqual(value, self.bzrworking)
        # Check that we actually have a non-empty branch here.
        branch = Branch.open(self.bzrworking)
        self.assertNotEqual(branch.revno(), 0)


from importd.tests import testutil
testutil.register(__name__)

