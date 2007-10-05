#!/usr/bin/python2.4
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# Author: Robert Collins <robertc@robertcollins.net>
#         David Allouche <david@allouche.net>

__metaclass__ = type

import unittest
import os
import datetime

from canonical.lp.dbschema import ImportStatus
from importd import JobStrategy
from importd.Job import Job, CopyJob
from importd.tests import testutil, helpers


class JobCreationTestCase(unittest.TestCase):

    def testConstruct(self):
        """Test creation of Job"""
        foo = Job()


class TestRunJob(helpers.SandboxTestCase):

    def setUp(self):
        helpers.SandboxTestCase.setUp(self)
        self.get_args = []
        self.strategy_args = []
        self.saved_jobstrategy_get = JobStrategy.get
        JobStrategy.get = self.mockGet

    def tearDown(self):
        helpers.SandboxTestCase.tearDown(self)
        JobStrategy.get = self.saved_jobstrategy_get

    def mockGet(self, *args):
        self.get_args.append(args)
        return self.mockStrategy

    def mockStrategy(self, *args):
        self.strategy_args.append(args)

    def makeJob(self):
        job = Job()
        job.RCS = 'CVS'
        job.TYPE = 'sync'
        return job

    def testRunJob(self):
        """test runJob calls the strategy"""
        job = self.makeJob()
        jobdir = self.sandbox.join('jobdir')
        job.runJob(jobdir)
        self.assertEqual(self.get_args, [('CVS', 'sync')])
        self.assertEqual(self.strategy_args, [(job, jobdir, None)])


class TestJobWorkingDir(helpers.JobTestCase):

    def testGetWorkingDir(self):
        """Job.getWorkingDir creates a directory with the right name"""
        basedir = self.sandbox.path
        # Try getWorkingDir with series 42, to check the format string
        self.job_helper.series_id = 42
        job = self.job_helper.makeJob()
        workingdir = self.sandbox.join('series-0000002a')
        path = job.getWorkingDir(basedir)
        self.assertEqual(path, workingdir)
        self.failUnless(os.path.exists(workingdir))
        # Try getWorkingDir with series 1, to check that the data is passed
        # around correctly.
        self.job_helper.series_id = 1
        job = self.job_helper.makeJob()
        workingdir = self.sandbox.join('series-00000001')
        path = job.getWorkingDir(basedir)
        self.assertEqual(path, workingdir)
        self.failUnless(os.path.exists(workingdir))


class TestNukeTargets(helpers.JobTestCase):
    """Run nukeTargets tests with BzrManager."""

    def testNukeTargets(self):
        # The scope of this test is:
        # - nukeTargets accepts a directory and a logger.
        # - nukeTargets deletes the workingdir.
        job = self.job_helper.makeJob()
        basedir = self.sandbox.path
        workingdir = job.getWorkingDir(basedir)
        assert os.path.exists(workingdir)
        # create a file to test recursive directory removal
        open(os.path.join(workingdir, 'some_file'), 'w').close()
        logger = testutil.makeSilentLogger()
        job.nukeTargets(basedir, logger)
        self.failIf(os.path.exists(workingdir))


class TestRepoType(unittest.TestCase):
    """I test repo identification works"""

    def testRsync(self):
        """rsync repositories are identified"""
        job = Job()
        job.repository = "rsync://phwoar"
        self.failUnless(job.repositoryIsRsync())

    def testTar(self):
        """tar balls are identified correctly"""
        job = Job()
        job.repository = "foo.tgz"
        self.failUnless(job.repositoryIsTar())
        job.repository = "foo.tar.gz"
        self.failUnless(job.repositoryIsTar())
        job.repository = "foo.tar.bz2"
        self.failUnless(job.repositoryIsTar())


class sampleData:
    package_import_id = 15
    package_import_distroseries_id = 3 # ubuntu hoary
    package_job_name = 'pkg-ubuntu-hoary-evolution-1.0'
    cvs_job_id = 3 # this is ProductSeries.id 3 for the evolution
    cvs_job_name = 'gnome-evolution-trunk'
    product_id = 5
    product_name = 'evolution'


class TestGetJob(helpers.ZopelessTestCase):
    '''can we get a job from the database'''

    def testGetBuilders(self):
        '''get a builders list from the db'''
        import importd.util # Local import to avoid circular import.
        importd_path = '/dummy/path/to/importd/package'
        push_prefix = '/dummy/prefix/to/push/branches/'
        source_repo = '/dummy/prefix/to/source/repo'
        jobs = importd.util.jobsFromDB(
            "slave_home", "archive_mirror_dir",
            autotest=False, push_prefix=push_prefix)
        self.assertEqual(len(jobs), 1)
        builders = importd.util.jobsBuilders(
            jobs, ["slavename"],
            importd_path=importd_path,
            push_prefix=push_prefix,
            source_repo=source_repo,
            autotest=False)
        self.assertEqual(len(builders), 1)

    def testGetPackageJob(self):
        '''get a usable package job from the db'''
        from canonical.launchpad.database import (
            SourcePackageRelease, DistroSeries)
        pkgid = sampleData.package_import_id
        drid = sampleData.package_import_distroseries_id
        spr = SourcePackageRelease.get(pkgid)
        dr = DistroSeries.get(drid)
        job = CopyJob().from_sourcepackagerelease(spr, dr)
        self.assertEqual(job.TYPE, 'sourcerer')
        self.assertEqual(job.RCS, 'package')
        self.assertEqual(job.product_id, sampleData.product_id)
        self.assertEqual(job.name, sampleData.package_job_name)

    def testGetCVSJob(self):
        """get a usable CVS job from the db"""
        from canonical.launchpad.database import ProductSeries
        job = CopyJob().from_series(ProductSeries.get(sampleData.cvs_job_id))
        self.assertEqual(job.TYPE, 'import')
        self.assertEqual(job.RCS, 'cvs')
        self.assertEqual(job.product_id, sampleData.product_id)
        self.assertEqual(job.name, sampleData.cvs_job_name)
        self.assertEqual(job.seriesID, sampleData.cvs_job_id)

    def testGetJobInterval(self):
        """get a CVS sync job with an syncinterval from the db"""
        from canonical.launchpad.database import ProductSeries
        series = ProductSeries.get(sampleData.cvs_job_id)
        interval = datetime.timedelta(days=1)
        series.syncinterval = interval
        series.enableAutoSync()
        series = ProductSeries.get(sampleData.cvs_job_id)
        self.assertEqual(series.syncinterval, interval)
        job = CopyJob().from_series(series)
        day_seconds = 24 * 60 * 60
        self.assertEqual(job.frequency, day_seconds)

    def testGetJobSeriesId(self):
        # Check that Job.from_series sets job.seriesID to the database id of
        # the ProductSeries.
        """get the seriesID for a job from the database"""
        from canonical.launchpad.database import ProductSeries
        series = ProductSeries.get(sampleData.cvs_job_id)
        job = CopyJob().from_series(series)
        self.assertEqual(job.seriesID, sampleData.cvs_job_id)


class MockJob(object):
    pass

class MockBuild(object):
    pass


class TestImportDBImplementor(helpers.ZopelessTestCase):
    """Assorted test cases for ImportDBImplementor.

    This class is responsible for updating the Launchpad database when buildbot
    jobs complete.
    """

    def setUp(self):
        helpers.ZopelessTestCase.setUp(self)
        self._impl = None
        self._refreshedBuilder = False
        self._refreshBuilderRerun = None

    def tearDown(self):
        self.series().dateautotested = None
        self.series().importstatus = ImportStatus.PROCESSING
        self.txnManager().commit()
        helpers.ZopelessTestCase.tearDown(self)

    def mockBuild(self):
        build = MockBuild()
        build.importDJob = MockJob()
        build.importDJob.seriesID = sampleData.cvs_job_id
        build.importDJob.RCS = 'cvs'
        return build

    def implementor(self):
        import importd.util
        if self._impl is None:
            build = self.mockBuild()
            self._impl = importd.util.ImportDBImplementor(build)
            self._impl.refreshBuilder = self._refreshBuilder
        return self._impl

    def _refreshBuilder(self, rerun):
        self._refreshedBuilder = True
        self._refreshBuilderRerun = rerun

    def series(self):
        return self.implementor().getSeries()

    def setUpTesting(self):
        """Set up the series to have importstatus = TESTING."""
        series = self.series()
        series.dateprocessapproved = None
        series.datesyncapproved = None
        series.datelastsynced = None
        series.importstatus = ImportStatus.TESTING

    def setUpProcessing(self):
        """Set up the series to have importstatus == PROCESSING."""
        series = self.series()
        series.datesyncapproved = None
        series.datelastsynced = None
        series.certifyForSync()
        assert series.importstatus == ImportStatus.PROCESSING
        assert series.datesyncapproved is None

    def setUpSyncing(self):
        """Set up the series to have importstatus == SYNCING."""
        self.setUpProcessing()
        series = self.series()
        series.enableAutoSync()
        assert series.importstatus == ImportStatus.SYNCING

    def txnManager(self):
        import importd.util
        return importd.util.getTxnManager()

    def testSetDateStarted(self):
        """ImportDBImplementor.setDateStarted changes datestarted."""
        self.series().datestarted = None
        self.implementor().setDateStarted()
        self.assert_(self.series().datestarted is not None)

    def testSetDateFinished(self):
        """ImportDBImplementor.setDateFinished changes datefinished."""
        self.series().datefinished = None
        self.implementor().setDateFinished()
        self.assert_(self.series().datefinished is not None)

    def testSetAutotestedSuccess(self):
        """ImportDBImplementor.setAutotested works on success."""
        self.series().dateautotested = None
        self.implementor().setAutotested(True)
        self.series().sync() # turn dateautotested into a datetime object
        self.assertEqual(self.series().importstatus, ImportStatus.AUTOTESTED)
        self.assertNotEqual(self.series().dateautotested, None)
        self.failUnless(self._refreshedBuilder)
        self.assertEqual(self._refreshBuilderRerun, False)

    def testSetAutotestedFailure(self):
        """ImportDBImplementor.setAutotested works on failure."""
        self.series().dateautotested = None
        self.implementor().setAutotested(False)
        self.assertEqual(self.series().importstatus, ImportStatus.TESTFAILED)
        self.assertEqual(self.series().dateautotested, None)
        self.failUnless(self._refreshedBuilder)
        self.assertEqual(self._refreshBuilderRerun, False)

    def testProcessingCompleteSuccess(self):
        """ImportDBImplementor.processingComplete works on success."""
        self.setUpProcessing()
        self.implementor().processingComplete(True)
        self.series().sync() # turn datesyncapproved into a datetime object
        self.assertEqual(self.series().importstatus, ImportStatus.SYNCING)
        self.assertNotEqual(self.series().datesyncapproved, None)
        self.failUnless(self._refreshedBuilder)
        self.assertEqual(self._refreshBuilderRerun, True)

    def testProcessingCompleteFailure(self):
        """ImportDBImplementor.processingComplete works on failure."""
        self.setUpProcessing()
        self.implementor().processingComplete(False)
        self.assertEqual(self.series().datesyncapproved, None)
        self.failIf(self._refreshedBuilder)

    def testStartBuild(self):
        """ImportDBImplementor.startBuild sets series and commits."""
        self.txnManager().begin()
        self.series().datestarted = None
        self.txnManager().commit()
        self.implementor().startBuild()
        # spiv who is reviewing this suggested this XXX abstraction
        # violation. RBC 20050608
        from canonical.database.sqlbase import SQLBase
        if SQLBase._connection is not None:
            self.txnManager().abort() # discard uncommitted changes
        self.assert_(self.series().datestarted is not None)

    def testBuildFinished(self):
        """ImportDBImplementor.buildFinished sets series and commits."""
        self.txnManager().begin()
        self.series().datefinished = None
        self.series().importstatus = ImportStatus.TESTING
        self.txnManager().commit()
        self.implementor().buildFinished(True)
        # spiv who is reviewing this suggested this XXX abstraction
        # violation. RBC 20050608
        from canonical.database.sqlbase import SQLBase
        if SQLBase._connection is not None:
            self.txnManager().abort() # discard uncommitted changes
        self.assert_(self.series().datefinished is not None)
        self.assertEqual(self.series().importstatus, ImportStatus.AUTOTESTED)

    def testBuildFinishedTestingSuccess(self):
        # buildFinished does not set datelastsynced when successful and the
        # status was TESTING (or anything but PROCESSING or SYNCING).
        self.txnManager().begin()
        self.setUpTesting()
        assert self.series().datelastsynced == None
        self.txnManager().commit()
        self.implementor().buildFinished(True)
        self.assertEqual(self.series().datelastsynced, None)

    def testBuildFinishedProcessingSuccess(self):
        # buildFinished sets datelastsynced when successful and the status was
        # PROCESSING.
        self.txnManager().begin()
        self.setUpProcessing()
        assert self.series().datelastsynced == None
        self.txnManager().commit()
        self.implementor().buildFinished(True)
        self.assertNotEqual(self.series().datelastsynced, None)

    def testBuildFinishedProcessingFailure(self):
        # buildFinished does not set datelastsynced when failing and the
        # status was PROCESSING.
        self.txnManager().begin()
        self.setUpProcessing()
        assert self.series().datelastsynced == None
        self.txnManager().commit()
        self.implementor().buildFinished(False)
        self.assertEqual(self.series().datelastsynced, None)

    def testBuildFinishedSyncingSuccess(self):
        # buildFinished sets datelastsynced when successful and the status
        # was SYNCING.
        self.txnManager().begin()
        self.setUpSyncing()
        self.series().datelastsynced = None
        self.txnManager().commit()
        self.implementor().buildFinished(True)
        self.assertNotEqual(self.series().datelastsynced, None)

    def testBuildFinishedSyncingFailure(self):
        # buildFinished does not set datelastsynced when failing and the status
        # was SYNCING.
        self.txnManager().begin()
        self.setUpSyncing()
        self.series().datelastsynced = None
        self.txnManager().commit()
        self.implementor().buildFinished(False)
        self.assertEqual(self.series().datelastsynced, None)


testutil.register(__name__)
