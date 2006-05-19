# Copyright (c) 2005 Canonical Ltd.
#!/usr/bin/env python
# Author: Robert Collins <robertc@robertcollins.net>
#         David Allouche <david@allouche.net>

import os
import unittest

from importd import JobStrategy
from importd.tests import testutil, helpers
from importd.tests.mock import MockDecorator, StubDecorator

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
    """Test the functionality of CVSStrategy."""

    def assertPatchlevels(self, master, mirror):
        self.assertMasterPatchlevels(master)
        self.assertMirrorPatchlevels(mirror)

    def setupSyncEnvironment(self):
        """I create a environment that a sync can be performed in"""
        self.cscvs_helper.setUpCvsImport()
        self.cscvs_helper.setUpCvsRevision()
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

    def testSync(self):
        """test performing a sync"""
        strategy = JobStrategy.CVSStrategy()
        logger = testutil.makeSilentLogger()
        self.assertRaises(AssertionError, strategy.sync, None, ".", None)
        self.assertRaises(AssertionError, strategy.sync, ".", None, None)
        self.assertRaises(AssertionError, strategy.sync, None, None, logger)
        aJob = self.job_helper.makeJob()
        self.setupSyncEnvironment()
        self.archive_manager.createMirror()
        basedir = self.sandbox_helper.sandbox_path
        # test that the initial sync does not rollback to mirror
        self.assertPatchlevels(master=['base-0'], mirror=[])
        strategy.sync(aJob, basedir, logger)
        self.assertPatchlevels(master=['base-0', 'patch-1'], mirror=[])
        # test that second sync does rollback to mirror
        self.mirrorBranch()
        self.assertMirrorPatchlevels(['base-0', 'patch-1'])
        self.baz_tree_helper.cleanUpTree()
        self.baz_tree_helper.setUpPatch()
        self.assertPatchlevels(master=['base-0', 'patch-1', 'patch-2'],
                               mirror=['base-0', 'patch-1'])
        strategy.sync(aJob, ".", logger)
        self.assertPatchlevels(master=['base-0', 'patch-1'],
                               mirror=['base-0', 'patch-1'])


class TestGetCVSDirFunctional(helpers.CscvsTestCase):
    """Feature tests for CVS tree handling in CVSStrategy."""

    def setUpCvsImport(self):
        self.cscvs_helper.setUpCvsImport()

    def setUpCvsRevision(self):
        self.cscvs_helper.setUpCvsRevision()

    def checkSourceFile(self, tree_path, revision):
        """Compare the contents of the source file to the expected value.

        :param tree_path: path of the tree to read the source file from.
        :param revision: revision of the sourcefile to expect.
        """
        aFile = open(os.path.join(tree_path, 'file1'))
        try:
            data = aFile.read()
        finally:
            aFile.close()
        self.assertEqual(data, self.cscvs_helper.sourcefile_data[revision])

    def makeStrategy(self, job):
        strategy = JobStrategy.CVSStrategy()
        strategy.aJob = job
        strategy.logger = testutil.makeSilentLogger()
        return strategy

    def callGetCVSDir(self):
        job = self.job_helper.makeJob()
        self.strategy = self.makeStrategy(job)
        basedir = self.sandbox_helper.sandbox_path
        self.cvspath = self.strategy.getCVSDirPath(job, basedir)
        path = self.strategy.getCVSDir(job, basedir)
        self.assertEqual(path, self.cvspath)

    def testGetCVSDir(self):
        # CVSStrategy.getCVSDir produces an updated CVS checkout and cache
        # initial run produces a checkout and a new catalog
        self.setUpCvsImport()
        self.callGetCVSDir()
        self.checkSourceFile(self.cvspath, 'import')
        catalog_path = os.path.join(self.cvspath, "CVS", "Catalog.sqlite")
        self.assertTrue(os.path.exists(catalog_path), 'catalog not created')
        main_branch = self.strategy._tree.catalog().getBranch('MAIN')
        self.assertEqual(len(main_branch), 2)
        # run after cvs commit, tree and catalog must be updated
        self.setUpCvsRevision()
        self.callGetCVSDir()
        self.checkSourceFile(self.cvspath, 'commit-1')
        main_branch = self.strategy._tree.catalog().getBranch('MAIN')
        self.assertEqual(len(main_branch), 3)

    def testRepositoryHasChanged(self):
        # CVSStrategy._repositoryHasChanged is False if on a fresh checkout
        self.setUpCvsImport()
        job = self.job_helper.makeJob()
        strategy = self.makeStrategy(job)
        basedir = self.sandbox_helper.sandbox_path
        strategy._cvsCheckOut(job, basedir)
        self.assertEqual(strategy._repositoryHasChanged(), False)
        tree = strategy._tree
        # CVSStrategy._repositoryHasChanged is True if the job.repository is a
        # plausible non-existent repository.
        job = self.job_helper.makeJob()
        job.repository = ':pserver:foo:aa@bad-host.example.com:/cvs'
        changed_strategy = self.makeStrategy(job)
        changed_strategy._tree = tree
        self.assertEqual(changed_strategy._repositoryHasChanged(), True)

    # TODO: functional test reCheckOutCvsDir must reget, but not touch the
    # Catalog.sqlite -- David Allouche 2006-05-19

    # TODO: functional test _repositoryHasChanged
    # fails if the modules do not match    
    # -- David Allouche 2006-05-19


class TestGetCVSDirUnits(helpers.CscvsTestCase):
    """Unit tests for CVS tree handling in CVSStrategy."""

    def setUp(self):
        helpers.CscvsTestCase.setUp(self)
        self.job = self.job_helper.makeJob()
        self.basedir = self.sandbox_helper.sandbox_path
        self.strategy = JobStrategy.CVSStrategy()
        self.strategy.aJob = self.job
        self.strategy.logger = testutil.makeSilentLogger()
        self.cvspath = self.strategy.getCVSDirPath(self.job, self.basedir)
        self.stub = StubDecorator()
        self.mock = MockDecorator()
        self.mock.override(self.strategy, [
            '_treeExists', '_repositoryHasChanged', '_existingCvsTree',
            '_updateCscvsCache', '_cvsCheckOut', '_cvsReCheckOut'])

    def callGetCVSDir(self):
        """Call getCVSDir and check the return value."""
        value = self.strategy.getCVSDir(self.job, self.basedir)
        self.assertEqual(value, self.cvspath)

    def testInitialCheckout(self):        
        # If the cvs path does not exist, CVSStrategy.getCVSDir calls
        # _cvsCheckOut and builds the cache.
        self.mock.setReturnValues({
            '_treeExists': [False],
            '_cvsCheckOut': [MockCvsTree()]})
        self.callGetCVSDir()
        self.mock.checkCall(self, 0, '_treeExists', self.cvspath)
        self.mock.checkCall(self, 1, '_cvsCheckOut', self.job, self.cvspath)
        self.mock.checkCall(self, 2, '_updateCscvsCache')
        self.mock.checkCallCount(self, 3)

    def testChangedRepository(self):
        # if the cvs path exists and has a different repository than the job:
        # CVSStrategy.getCVSDIR calls _cvsReCheckout and updates the cache.
        tree = MockCvsTree()
        tree_repository = MockCvsRepository()
        tree_repository.root = 'foo'
        self.stub.define(tree, {
            'repository': tree_repository})
        self.stub.override(self.strategy, {
            '_repositoryHasChanged': True})
        self.mock.setReturnValues({
            '_treeExists': [True],
            '_existingCvsTree': [tree]})
        self.callGetCVSDir()
        self.mock.checkCall(self, 0, '_treeExists', self.cvspath)
        self.mock.checkCall(self, 1, '_existingCvsTree', self.cvspath)
        # re-checkout, we want to preserve the catalog!
        self.mock.checkCall(self, 2, '_cvsReCheckOut', self.job, self.cvspath)
        self.mock.checkCall(self, 3, '_updateCscvsCache')
        self.mock.checkCallCount(self, 4)

    def testModifiedTree(self):
        # if the cvs path exists, has the correct repository but the tree has
        # changes: CVSStrategy.getCVSDir recheckouts the tree and updates the
        # cache.
        tree = MockCvsTree()
        self.stub.define(tree, {
            'has_changes': True})
        self.stub.override(self.strategy, {
            '_repositoryHasChanged': False})
        self.mock.setReturnValues({
            '_treeExists': [True],
            '_existingCvsTree': [tree]})
        self.callGetCVSDir()
        self.mock.checkCall(self, 0, '_treeExists', self.cvspath)
        self.mock.checkCall(self, 1, '_existingCvsTree', self.cvspath)
        # re-checkout, we want to preserve the catalog!
        self.mock.checkCall(self, 2, '_cvsReCheckOut', self.job, self.cvspath)
        self.mock.checkCall(self, 3, '_updateCscvsCache')
        self.mock.checkCallCount(self, 4)
        
    def testExistingCheckout(self):
        # if the cvs path exists, has the correct repository, and the tree has
        # no change: CVSStrategy.getCVSDir updates  the tree and the cache.
        tree = MockCvsTree()
        self.mock.define(tree, ['update'])
        self.stub.define(tree, {
            'has_changes': False})
        self.stub.override(self.strategy, {
            '_repositoryHasChanged': False})
        self.mock.setReturnValues({
            '_treeExists': [True],
            '_existingCvsTree': [tree]})
        self.callGetCVSDir()
        self.mock.checkCall(self, 0, '_treeExists', self.cvspath)
        self.mock.checkCall(self, 1, '_existingCvsTree', self.cvspath)
        # update, we want to preserve the catalog!
        self.mock.checkCall(self, 2, 'update')
        self.mock.checkCall(self, 3, '_updateCscvsCache')
        self.mock.checkCallCount(self, 4)


class MockCvsRepository(object):
    """Mock CVS.Repository, for testing."""
    pass

class MockCvsTree(object):
    """Mock CVS.WorkingTree, for testing."""
    pass


testutil.register(__name__)
