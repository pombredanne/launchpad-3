#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# Author: Robert Collins <robertc@robertcollins.net>
#         David Allouche <david@allouche.net>

import unittest
import sys
import os
import logging
import shutil
import datetime

import gnarly.process
import gnarly.process.unix_process
gnarly.process.Popen = gnarly.process.unix_process.Popen

import pybaz.errors
import pybaz as arch
import pybaz.backends.forkexec
pybaz.backend.spawning_strategy = \
    pybaz.backends.forkexec.PyArchSpawningStrategy

from importd.archivemanager import ArchiveManager
from importd.Job import Job, CopyJob
from importd import JobStrategy
from importd.tests import TestUtil, helpers


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
        jobdir = self.sandbox_helper.path('jobdir')
        job.runJob(jobdir)
        self.assertEqual(self.get_args, [('CVS', 'sync')])
        self.assertEqual(self.strategy_args, [(job, jobdir, None)])


class TestBazFullPackage(unittest.TestCase):

    def testFullPackageVersion(self):
        """test full package version is calculated correctly"""
        aJob = Job()
        aJob.archivename = "archive"
        aJob.category = "category"
        aJob.branchto = "branch"
        aJob.archversion = "1"
        self.assertEqual(
            aJob.bazFullPackageVersion(), "archive/category--branch--1")


class TestJobWorkingDir(helpers.ArchiveManagerTestCase):
    
    def testGetWorkingDir(self):
        """Job.getWorkingDir creates a directory with the right name"""
        job = self.job_helper.makeJob()
        basedir = self.sandbox_helper.sandbox_path
        version = self.archive_manager_helper.makeVersion()
        workingdir = self.sandbox_helper.path(version.fullname)
        path = job.getWorkingDir(basedir)
        self.assertEqual(path, workingdir)
        self.failUnless(os.path.exists(workingdir))


class NukeTargetJobHelper(helpers.ArchiveManagerTestCase.jobHelperType):
    """Job Factory for nukeTargets test cases."""

    def makeJob(self):
        job = helpers.ArchiveManagerTestCase.jobHelperType.makeJob(self)
        job.nukeMasterCalled = 0
        class instrumentedArchiveManager(ArchiveManager):
            def nukeMaster(self):
                job.nukeMasterCalled += 1
                ArchiveManager.nukeMaster(self)
        def makeInstrumentedArchiveManager():
            return instrumentedArchiveManager(job)
        job.makeArchiveManager = makeInstrumentedArchiveManager
        return job

class TestNukeTargets(helpers.ArchiveManagerTestCase):

    jobHelperType = NukeTargetJobHelper

    def testNukeTargets(self):
        """nukeTarget removes tree and calls ArchiveManager.nukeMaster"""
        job = self.job_helper.makeJob()
        basedir = self.sandbox_helper.sandbox_path
        workingdir = job.getWorkingDir(basedir)
        assert os.path.exists(workingdir)
        # create a file to test recursive directory removal
        open(os.path.join(workingdir, 'some_file'), 'w').close()
        logger = TestUtil.makeSilentLogger()
        assert job.nukeMasterCalled == 0
        job.nukeTargets(basedir, logger)
        self.failIf(os.path.exists(workingdir))
        self.assertEqual(job.nukeMasterCalled, 1)


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
    package_import_distrorelease_id = 3 # ubuntu hoary
    package_job_name = 'pkg-ubuntu-hoary-evolution-1.0'
    cvs_job_id = 3 # this is ProductSeries.id 3 for the evolution
    cvs_job_name = 'gnome-evolution-main'
    product_id = 5
    product_name = 'evolution'


class TestGetJob(helpers.ZopelessTestCase):
    '''can we get a job from the database'''

    def testGetBuilders(self):
        '''get a builders list from the db'''
        import importd.util
        from canonical.lp.dbschema import ImportStatus
        jobs = importd.util.jobsFromDB("slave_home",
                                       "archive_mirror_dir",
                                       autotest = False)
        self.assertEqual(len(jobs), 1)
        builders = importd.util.jobsBuilders(jobs, ["slavename"], autotest=False)
        self.assertEqual(len(builders), 1)

    def testGetPackageJob(self):
        '''get a usable package job from the db'''
        from canonical.launchpad.database import SourcePackage, \
                SourcePackageRelease, DistroRelease
        pkgid = sampleData.package_import_id
        drid = sampleData.package_import_distrorelease_id
        spr = SourcePackageRelease.get(pkgid)
        dr = DistroRelease.get(drid)
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

    def testGetJobTarget(self):
        """get the arch target details for a job from the db"""
        from canonical.launchpad.database import ProductSeries
        series = ProductSeries.get(sampleData.cvs_job_id)
        series.targetarcharchive = 'joe@example.org'
        series.targetarchcategory = 'foo'
        series.targetarchbranch = 'bar'
        series.targetarchversion = '4.2'
        job = CopyJob().from_series(series)
        self.assertEqual(job.archivename, 'joe@example.org')
        self.assertEqual(job.category, 'foo')
        self.assertEqual(job.branchto, 'bar')
        self.assertEqual(job.archversion, '4.2')

    def testGetJobTargetNull(self):
        """get automatic target for a job without arch details in the db"""
        from canonical.launchpad.database import ProductSeries
        from canonical.lp.dbschema import ImportStatus
        series = ProductSeries.get(sampleData.cvs_job_id)
        series.importstatus = ImportStatus.TESTING
        series.product.name = 'foo'
        series.name = 'bar'
        series.targetarcharchive = None
        series.targetarchcategory = None
        series.targetarchbranch = None
        series.targetarchversion = None
        job = CopyJob().from_series(series)
        self.assertEqual(job.archivename, 'foo@autotest.bazaar.ubuntu.com')
        self.assertEqual(job.category, 'foo')
        self.assertEqual(job.branchto, 'bar-TEST-DO-NOT-USE')
        self.assertEqual(job.archversion, '0')


class MockJob(object):
    pass

class TestInterlockNonDB(unittest.TestCase):

    """Interlock tests that do not need the database."""

    def mockJob(self, name, product_id, rcs):
        job = MockJob()
        job.name = name
        job.product_id = product_id
        job.RCS = rcs
        return job

    def testNoJob(self):
        """jobsInterlocks works with an empty job list."""
        import importd.util
        interlocks = importd.util.jobsInterlocks([])
        self.assertEqual(interlocks, [])

    def testAnonInterlock(self):
        """anonymousInterlock separates one package and one cvs"""
        import importd.util
        cvs = self.mockJob('foo-head', 1, 'cvs')
        pkg = self.mockJob('foo-warty', 1, 'package')
        interlock = importd.util.anonymousInterlock([pkg, cvs])
        self.assertEqual(2, len(interlock))
        self.assertEqual([1,1], map(len, interlock))
        self.assertEqual(cvs.name, interlock[0][0])
        self.assertEqual(pkg.name, interlock[1][0])

    def testAnonNoInterlock(self):
        """anonymousInterlock handles absence of interlock"""
        import importd.util
        cvs = self.mockJob('foo', 1, 'cvs')
        pkg = self.mockJob('foo', 1, 'package')
        interlock = importd.util.anonymousInterlock([pkg])
        self.assertEqual(interlock, None)
        interlock = importd.util.anonymousInterlock([cvs])
        self.assertEqual(interlock, None)

    def testNoInterlock(self):
        """jobsInterlocks does not interlock different products."""
        import importd.util
        cvs = self.mockJob('foo-head', 1, 'cvs')
        pkg = self.mockJob('bar-warty', 2, 'package')
        interlocks = importd.util.jobsInterlocks([cvs, pkg])
        self.assertEqual([], interlocks)


class TestInterlockDB(helpers.ZopelessTestCase):
    """Interlock tests that need database access."""

    def testNameInterlock(self):
        """nameInterlock works"""
        import importd.util
        anon = (object(), object())
        inter = importd.util.nameInterlock(sampleData.product_id, anon)
        self.assertEqual(inter, (sampleData.product_name,) + anon)

    def testBuildersInterlocksFeature(self):
        """buildersInterlocks works with sample data"""
        import importd.util
        from canonical.launchpad.database import SourcePackage, \
                SourcePackageRelease, DistroRelease
        from canonical.lp.dbschema import ImportStatus
        pkgid = sampleData.package_import_id
        drid = sampleData.package_import_distrorelease_id
        spr = SourcePackageRelease.get(pkgid)
        dr = DistroRelease.get(drid)
        pkgjob = CopyJob().from_sourcepackagerelease(spr, dr)
        jobs = importd.util.jobsFromDB("slave_home",
                                       "archive_mirror_dir",
                                       autotest = False)
        jobs.append(pkgjob)
        builders = []
        interlocks = importd.util.jobsInterlocks(jobs)
        self.assertEqual(1, len(interlocks))
        interlock = interlocks[0]
        self.assertEqual(sampleData.product_name, interlock[0])
        self.assertEqual([1, 1], map(len, interlock[1:]))
        self.assertEqual(sampleData.cvs_job_name, interlock[1][0])
        self.assertEqual(sampleData.package_job_name, interlock[2][0])


class MockBuild(object):
    pass


class TestImpordDBuild(helpers.ZopelessTestCase):

    def setUp(self):
        helpers.ZopelessTestCase.setUp(self)
        self._impl = None
        self._refreshedBuilder = False
        self._refreshBuilderRerun = None

    def tearDown(self):
        from canonical.lp.dbschema import ImportStatus
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
        from canonical.lp.dbschema import ImportStatus
        self.series().dateautotested = None
        self.implementor().setAutotested(True)
        self.series().sync() # turn dateautotested into a datetime object
        self.assertEqual(self.series().importstatus, ImportStatus.AUTOTESTED)
        self.assertNotEqual(self.series().dateautotested, None)
        self.failUnless(self._refreshedBuilder)
        self.assertEqual(self._refreshBuilderRerun, False)

    def testSetAutotestedFailure(self):
        """ImportDBImplementor.setAutotested works on failure."""
        from canonical.lp.dbschema import ImportStatus
        self.series().dateautotested = None
        self.implementor().setAutotested(False)
        self.assertEqual(self.series().importstatus, ImportStatus.TESTFAILED)
        self.assertEqual(self.series().dateautotested, None)
        self.failUnless(self._refreshedBuilder)
        self.assertEqual(self._refreshBuilderRerun, False)

    def testProcessingCompleteSuccess(self):
        """ImportDBImplementor.processingComplete works on success."""
        from canonical.lp.dbschema import ImportStatus
        self.series().importstatus = ImportStatus.PROCESSING
        self.series().datesyncapproved = None
        self.series().syncinterval = datetime.timedelta(1)
        self.implementor().processingComplete(True)
        self.series().sync() # turn datesyncapproved into a datetime object
        self.assertEqual(self.series().importstatus, ImportStatus.SYNCING)
        self.assertNotEqual(self.series().datesyncapproved, None)
        self.failUnless(self._refreshedBuilder)
        self.assertEqual(self._refreshBuilderRerun, True)

    def testProcessingCompleteFailure(self):
        """ImportDBImplementor.processingComplete works on failure."""
        from canonical.lp.dbschema import ImportStatus
        self.series().importstatus = ImportStatus.PROCESSING
        self.series().datesyncapproved = None
        self.assertEqual(self.series().importstatus, ImportStatus.PROCESSING)
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
        from canonical.lp.dbschema import ImportStatus
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


TestUtil.register(__name__)
