# Copyright (c) 2005 Canonical Ltd.
#!/usr/bin/env python
# Author: Robert Collins <robertc@robertcollins.net>
#         David Allouche <david@allouche.net>

import os
import logging
import unittest

from importd import JobStrategy
from importd.tests import TestUtil, helpers


class TestCvsStrategyCreation(unittest.TestCase):

    def assertInstanceMethod(self, method, class_, name):
        self.assertEqual(method.im_class, class_)
        self.assertEqual(method.im_func.__name__, name)

    def testGet(self):
        """Test getting a Strategy"""
        CVS_import = JobStrategy.get("CVS", "import")
        self.assertInstanceMethod(CVS_import, JobStrategy.CVSStrategy, 'Import')
        cvs_import = JobStrategy.get("cvs", "import")
        self.assertInstanceMethod(cvs_import, JobStrategy.CVSStrategy, 'Import')
        CVS_sync = JobStrategy.get("CVS", "sync")
        self.assertInstanceMethod(CVS_sync, JobStrategy.CVSStrategy, 'sync')
        cvs_sync = JobStrategy.get("cvs", "sync")
        self.assertInstanceMethod(cvs_sync, JobStrategy.CVSStrategy, 'sync')

    def testGetInvalidRCS(self):
        """Test getting with invalid RCS"""
        self.assertRaises(KeyError, JobStrategy.get, "blargh", "sync")

    def testGetInvalidType(self):
        """Test getting with invalid type"""
        self.assertRaises(KeyError, JobStrategy.get, "CVS", "blargh")


class TestCvsStrategy(helpers.CscvsTestCase):
    """I test the functionality of CVSStrategy"""

    def assertPatchlevels(self, master, mirror):
        self.assertMasterPatchlevels(master)
        self.assertMirrorPatchlevels(mirror)

    def setupSyncEnvironment(self):
        """I create a environment that a sync can be performed in"""
        self.cscvs_helper.setUpCvsToSyncWith()
        self.cscvs_helper.doRevisionOne()

    def testGetWorkingDir(self):
        """test that the working dir is calculated & created correctly"""
        strategy = JobStrategy.CVSStrategy()
        job = self.job_helper.makeJob()
        basedir = self.sandbox_helper.sandbox_path
        version = self.archive_manager_helper.makeVersion()
        workingdir = self.sandbox_helper.path(version.fullname)
        self.assertEqual(strategy.getWorkingDir(job, basedir), workingdir)
        self.failUnless(os.path.exists(workingdir))

    def testGetCVSDir(self):
        """test ensuring we have an updated CVS dir with a cscvs cache in it"""
        strategy = JobStrategy.CVSStrategy()
        self.setupSyncEnvironment()
        basedir = self.sandbox_helper.sandbox_path
        job = self.job_helper.makeJob()
        cvspath = strategy.getCVSDirPath(job, basedir)
        strategy.aJob = job
        strategy.logger = logging
        path = strategy.getCVSDir(job, basedir)
        self.assertEqual(path, cvspath)
        catalog_path = os.path.join(cvspath, "CVS", "Catalog.sqlite")
        self.failUnless(os.path.exists(catalog_path), 'catalog not created')

    def testSync(self):
        """test performing a sync"""
        strategy = JobStrategy.CVSStrategy()
        self.assertRaises(AssertionError, strategy.sync, None, ".", None)
        self.assertRaises(AssertionError, strategy.sync, ".", None, None)
        self.assertRaises(AssertionError, strategy.sync, None, None, logging)
        aJob = self.job_helper.makeJob()
        self.setupSyncEnvironment()
        self.archive_manager.createMirror()
        basedir = self.sandbox_helper.sandbox_path
        # test that the initial sync does not rollback to mirror
        self.assertPatchlevels(master=['base-0'], mirror=[])
        strategy.sync(aJob, basedir, logging)
        self.assertPatchlevels(master=['base-0', 'patch-1'], mirror=[])
        # test that second sync does rollback to mirror
        self.mirrorBranch()
        self.assertMirrorPatchlevels(['base-0', 'patch-1'])
        self.baz_tree_helper.cleanUpTree()
        self.baz_tree_helper.setUpPatch()
        self.assertPatchlevels(master=['base-0', 'patch-1', 'patch-2'],
                               mirror=['base-0', 'patch-1'])
        strategy.sync(aJob, ".", logging)
        self.assertPatchlevels(master=['base-0', 'patch-1'],
                               mirror=['base-0', 'patch-1'])


TestUtil.register(__name__)
