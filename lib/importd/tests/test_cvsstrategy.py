# Copyright (c) 2005 Canonical Ltd.
#!/usr/bin/env python
# Author: Robert Collins <robertc@robertcollins.net>
#         David Allouche <david@allouche.net>

import os
import unittest

from importd import JobStrategy
from importd.tests import testutil, helpers

import CVS


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


class CvsStrategyTestCase(helpers.CscvsTestCase):
    """Common base for CVSStrategy test case classes."""

    def setUp(self):
        helpers.CscvsTestCase.setUp(self)
        self.job = self.job_helper.makeJob()
        self.logger = testutil.makeSilentLogger()
        self.sandbox = self.sandbox_helper.sandbox_path
        self.cvspath = os.path.join(self.sandbox, 'importd@example.com',
                                    'test--branch--0', 'cvsworking')

    def assertSourceFile(self, revision):
        """Compare the contents of the source file to the expected value.

        :param revision: revision of the sourcefile to expect.
        """
        aFile = open(os.path.join(self.cvspath, 'file1'))
        try:
            data = aFile.read()
        finally:
            aFile.close()
        self.assertEqual(data, self.cscvs_helper.sourcefile_data[revision])

    def writeSourceFile(self, data):
        """Change the contents of the source file.

        :param data: data to write to the source file.
        """
        aFile = open(os.path.join(self.cvspath, 'file1'), 'w')
        aFile.write(data)
        aFile.close()


class TestCvsStrategy(CvsStrategyTestCase):
    """Test the functionality of CVSStrategy."""

    def setUp(self):
        CvsStrategyTestCase.setUp(self)
        self.strategy = self.makeStrategy(self.job)

    def makeStrategy(self, job):
        strategy = JobStrategy.CVSStrategy()
        strategy.aJob = job
        strategy.logger = self.logger
        return strategy

    def assertPatchlevels(self, master, mirror):
        self.assertMasterPatchlevels(master)
        self.assertMirrorPatchlevels(mirror)

    def setupSyncEnvironment(self):
        """I create a environment that a sync can be performed in"""
        self.cscvs_helper.setUpCvsImport()
        self.cscvs_helper.setUpCvsRevision()
        self.cscvs_helper.doRevisionOne()

    def testGetCvsDirPath(self):
        # CVSStrategy.getCvsDirPath is consistent with self.cvspath
        cvspath = self.strategy.getCVSDirPath(self.job, self.sandbox)
        self.assertEqual(cvspath, self.cvspath)

    def testGetWorkingDir(self):
        # test that the working dir is calculated & created correctly
        version = self.archive_manager_helper.makeVersion()
        workingdir = self.sandbox_helper.path(version.fullname)
        self.assertEqual(
            self.strategy.getWorkingDir(self.job, self.sandbox), workingdir)
        self.failUnless(os.path.exists(workingdir))

    def testSync(self):
        # Feature test for performing a CVS sync.
        strategy = self.strategy
        logger = self.logger

        # XXX: I am not sure what these tests are for
        # -- David Allouche 2006-06-06
        self.assertRaises(AssertionError, strategy.sync, None, ".", None)
        self.assertRaises(AssertionError, strategy.sync, ".", None, None)
        self.assertRaises(AssertionError, strategy.sync, None, None, logger)

        self.setupSyncEnvironment()
        self.archive_manager.createMirror()
        # test that the initial sync does not rollback to mirror
        self.assertPatchlevels(master=['base-0'], mirror=[])
        self.strategy.sync(self.job, self.sandbox, self.logger)
        self.assertPatchlevels(master=['base-0', 'patch-1'], mirror=[])
        # test that second sync does rollback to mirror
        self.mirrorBranch()
        self.assertMirrorPatchlevels(['base-0', 'patch-1'])
        self.baz_tree_helper.cleanUpTree()
        self.baz_tree_helper.setUpPatch()
        self.assertPatchlevels(master=['base-0', 'patch-1', 'patch-2'],
                               mirror=['base-0', 'patch-1'])
        self.strategy.sync(self.job, ".", self.logger)
        self.assertPatchlevels(master=['base-0', 'patch-1'],
                               mirror=['base-0', 'patch-1'])


class CvsWorkingTreeTestsMixin:
    """Common tests for CVS working tree handling.

    This class defines test methods, and is inherited by actual TestCase
    classes that implement different environments to run the tests.
    """

    def testCvsTreeExists(self):
        # CvsWorkingTree.cvsTreeExists is false if the tree does not exist
        self.assertEqual(self.working_tree.cvsTreeExists(), False)

    def testExistingCvsTree(self):
        # CvsWorkingTree.cscvsCvsTree fails if the tree does not exist
        self.assertRaises(AssertionError, self.working_tree.cscvsCvsTree)

    def testCvsCheckOut(self):
        # TODO: break this test into smaller more focused tests
        # -- David Allouche 2006-06-06

        # CvsWorkingTree.cvsCheckOut works if the tree does not exist
        self.setUpCvsImport()
        self.working_tree.cvsCheckOut(self.repository)
        self.assertSourceFile('import')
        # CvsWorkingTree.cvsTreeExists is true after a checkout
        self.assertEqual(self.working_tree.cvsTreeExists(), True)
        # CvsWorkingTree.cscvsCvsTree works after a checkout
        # Do not check the class of the tree because it would prevent running
        # this test with a stub tree.
        tree = self.working_tree.cscvsCvsTree()
        self.assertNotEqual(tree, None)
        # CvsWorkingTree.cvsCheckOut fails if the tree exists
        self.assertRaises(AssertionError,
                          self.working_tree.cvsCheckOut, self.repository)

    # TODO: write test for error handling in cvsCheckOut. If we call the
    # back-end get and it fails, any checkout directory created by the failed
    # command must be deleted and the exception must be passed up.
    # -- David Allouche 2006-06-06

    def testCvsUpdate(self):
        # After a checkout, the CVS tree can be successfully updated
        self.setUpCvsImport()
        self.working_tree.cvsCheckOut(self.repository)
        self.assertSourceFile('import')
        self.setUpCvsRevision()
        self.working_tree.cvsUpdate()
        self.assertSourceFile('commit-1')

    def testCvsReCheckOut(self):
        # TODO: break this test into smaller more focused tests
        # -- David Allouche 2006-06-06

        # CvsWorkingTree.cvsReCheckOut fails if there is no checkout
        self.assertRaises(AssertionError,
                          self.working_tree.cvsReCheckOut, self.repository)
        # Set up a checkout with changes
        self.setUpCvsImport()
        self.working_tree.cvsCheckOut(self.repository)
        self.assertSourceFile('import')
        self.assertEqual(self.working_tree.cvsTreeHasChanges(), False)
        self.writeSourceFile('changed data\n')
        self.assertEqual(self.working_tree.cvsTreeHasChanges(), True)
        # CvsWorkingTree.cvsReCheckOut reverts source changes
        self.working_tree.cvsReCheckOut(self.repository)
        self.assertSourceFile('import')
        self.assertEqual(self.working_tree.cvsTreeHasChanges(), False)

    def testRepositoryHasChanged(self):
        # TODO: break this test into smaller more focused tests
        # -- David Allouche 2006-06-06

        self.setUpCvsImport()
        # CvsWorkingTree.repositoryHasChanged fails if there is no checkout
        self.assertRaises(AssertionError,
            self.working_tree.repositoryHasChanged, self.repository)
        # CvsWorkingTree.repositoryHasChanged is False on a fresh checkout
        self.working_tree.cvsCheckOut(self.repository)
        has_changed = self.working_tree.repositoryHasChanged(self.repository)
        self.assertEqual(has_changed, False)
        # CvsWorkingTree.repositoryHasChanged is True if the repository is a
        # plausible non-existent repository.
        changed_cvsroot = ':pserver:foo:aa@bad-host.example.com:/cvs'
        repository = self.makeCvsRepository(changed_cvsroot)
        has_changed = self.working_tree.repositoryHasChanged(repository)
        self.assertEqual(has_changed, True)

    def testUpdateCscvsCache(self):
        # TODO: break this test into smaller more focused tests
        # -- David Allouche 2006-06-06

        # CvsWorkingTree.updateCscvsCache fails if there is no checkout
        self.assertRaises(AssertionError, self.working_tree.updateCscvsCache)
        # CvsWorkingTree.updatesCscvsCache creates the cscvs cache
        self.setUpCvsImport()
        self.working_tree.cvsCheckOut(self.repository)
        self.working_tree.updateCscvsCache()
        self.checkCscvsCache()
        self.checkCatalogMainLength(2)
        # CvsWorkingTree.updateCscvsCache updates the cscvs cache
        self.setUpCvsRevision()
        self.working_tree.cvsUpdate()
        self.checkCatalogMainLength(2)
        self.working_tree.updateCscvsCache()
        self.checkCatalogMainLength(3)

    # TODO: functional test reCheckOutCvsDir must reget, but not touch the
    # Catalog.sqlite -- David Allouche 2006-05-19

    # TODO: functional test _repositoryHasChanged
    # fails if the modules do not match
    # -- David Allouche 2006-05-19


class TestCvsWorkingTreeFunctional(CvsWorkingTreeTestsMixin,
                                   CvsStrategyTestCase):
    """Functional tests for CVS working tree handling."""

    # This class implements the environment for running
    # CvsWorkingTreeTestsMixin tests with real CVS repositories and checkouts

    def setUp(self):
        CvsStrategyTestCase.setUp(self)
        self.job.getWorkingDir(self.sandbox) # create parents of cvspath
        self.working_tree = JobStrategy.CvsWorkingTree(
            self.job, self.cvspath, self.logger)
        self.repository = self.makeCvsRepository(self.job.repository)

    def makeCvsRepository(self, cvsroot):
        return CVS.Repository(cvsroot, self.logger)

    def setUpCvsImport(self):
        self.cscvs_helper.setUpCvsImport()

    def setUpCvsRevision(self):
        self.cscvs_helper.setUpCvsRevision()

    def checkCscvsCache(self):
        catalog_path = os.path.join(self.cvspath, "CVS", "Catalog.sqlite")
        self.assertTrue(os.path.exists(catalog_path), 'catalog not created')

    def checkCatalogMainLength(self, length):
        tree = self.working_tree.cscvsCvsTree()
        main_branch = tree.catalog().getBranch('MAIN')
        self.assertEqual(len(main_branch), length)

    def testCvsTreeExistsSanity(self):
        # CvsWorkingTree.cvsTreeExists fails if the path exists and is not a
        # tree
        os.mkdir(self.cvspath)
        self.assertRaises(AssertionError, self.working_tree.cvsTreeExists)


class FakeCvsWorkingTreeTestCase(CvsStrategyTestCase):
    """Base class for tests using the fake CVS environment."""

    # This class implement the environment for running CvsWorkingTreeTestsMixin
    # tests on fake CVS repositories and checkouts. These fake objects are then
    # used for CVSStrategy unit tests.

    def setUp(self):
        CvsStrategyTestCase.setUp(self)
        self.job.getWorkingDir(self.sandbox) # create parents of cvspath
        self.working_tree = FakeCvsWorkingTree(
            self.job, self.cvspath, self.logger)
        self.repository = self.makeCvsRepository(self.job.repository)
        self._cvs_status = None

    def makeCvsRepository(self, cvsroot):
        return FakeCvsRepository(cvsroot, self.cscvs_helper)

    def setUpCvsImport(self):
        assert self.repository._revision is None
        self.repository._revision = 'import'
        self.repository._main_length = 2

    def setUpCvsRevision(self):
        assert self.repository._revision == 'import'
        self.repository._revision = 'commit-1'
        self.repository._main_length = 3

    def assertSourceFile(self, revision):
        assert self.working_tree._has_tree
        self.assertFalse(self.working_tree._tree_has_changes)
        self.assertEqual(self.working_tree._tree_revision, revision)

    def writeSourceFile(self, data):
        unused = data
        assert self.working_tree._has_tree
        self.working_tree._tree_has_changes = True

    def checkCscvsCache(self):
        self.assertNotEqual(self.working_tree._has_catalog, None)

    def checkCatalogMainLength(self, length):
        assert self.working_tree._has_tree
        assert self.working_tree._has_catalog
        self.assertEqual(self.working_tree._catalog_main_length, length)


class TestCvsWorkingTreeFake(CvsWorkingTreeTestsMixin,
                             FakeCvsWorkingTreeTestCase):
    """Check that the Fake CvsWorkingTree pass CvsWorkingTreeTestsMixin tests.
    """


class FakeCvsWorkingTree:
    """Fake object to use in place of JobStrategy.CvsWorkingTree."""

    def __init__(self, job, path, logger):
        self._job = job
        self._path = path
        self.logger = logger
        self.calls = []
        self._has_tree = False
        self._has_catalog = False
        self._tree_repository = None
        self._tree_revision = None
        self._tree_has_changes = None
        self._catalog_main_length = None

    def cvsCheckOut(self, repository):
        self.calls.append(('cvsCheckOut', repository))
        assert not self._has_tree
        self._has_tree = True
        self._tree_revision = repository._revision
        self._tree_repository = repository
        self._tree_has_changes = False

    def cvsTreeExists(self):
        return self._has_tree

    def cscvsCvsTree(self):
        self.calls.append(('cscvsCvsTree',))
        assert self._has_tree
        return FakeCscvsCvsTree()

    def cvsReCheckOut(self, repository):
        self.calls.append(('cvsReCheckOut', repository))
        assert self._has_tree
        self._tree_revision = repository._revision
        self._tree_repository = repository
        self._tree_has_changes = False

    def repositoryHasChanged(self, repository):
        assert self._has_tree
        return self._tree_repository != repository

    def updateCscvsCache(self):
        assert self._has_tree
        self.calls.append(('updateCscvsCache',))
        self._has_catalog = True
        self._catalog_main_length = self._tree_repository._main_length

    def cvsTreeHasChanges(self):
        assert self._has_tree
        return self._tree_has_changes

    def cvsUpdate(self):
        self.calls.append(('cvsUpdate',))
        assert self._has_tree
        assert not self._tree_has_changes
        self._tree_revision = self._tree_repository._revision


class FakeCscvsCvsTree:
    """Fake object to use in place of JobStrategy.CvsWorkingTree."""


class FakeCvsRepository:
    """Fake object to use in place of CVS.Repository."""

    def __init__(self, cvsroot, cscvs_helper):
        self.root = cvsroot
        self._revision = None
        self._main_length = None
        self._cscvs_helper = cscvs_helper

    def __cmp__(self, other):
        """Test on the logical identity rather than object adddress."""
        return cmp(self.root, other.root)


class TestGetCVSDirUnits(FakeCvsWorkingTreeTestCase):
    """Unit tests for CVS tree handling in CVSStrategy."""

    def setUp(self):
        FakeCvsWorkingTreeTestCase.setUp(self)
        self.strategy = JobStrategy.CVSStrategy()
        self.strategy.aJob = self.job
        self.strategy.logger = self.logger
        self.strategy._working_tree_factory = self.fakeWorkingTreeFactory
        self.strategy.repo = self.fakeRepositoryFactory

    def fakeWorkingTreeFactory(self, job, path, logger):
        self.assertEqual(job, self.job)
        self.assertEqual(path, self.cvspath)
        self.assertEqual(logger, self.logger)
        return self.working_tree

    def fakeRepositoryFactory(self):
        return self.repository

    def callGetCVSDir(self):
        """Call getCVSDir and check the return value."""
        value = self.strategy.getCVSDir(self.job, self.sandbox)
        self.assertEqual(value, self.cvspath)

    def testInitialCheckout(self):
        # If the cvs path does not exist, CVSStrategy.getCVSDir calls
        # _cvsCheckOut and builds the cache.
        self.callGetCVSDir()
        self.assertEqual(self.working_tree.calls, [
            ('cvsCheckOut', self.repository),
            ('updateCscvsCache',),
            ('cscvsCvsTree',)])

    def testChangedRepository(self):
        # if the cvs path exists and has a different repository than the job:
        # CVSStrategy.getCVSDIR calls _cvsReCheckout and updates the cache.
        self.working_tree.cvsCheckOut(self.repository)
        self.working_tree._tree_repository = self.makeCvsRepository('foo')
        assert self.working_tree.repositoryHasChanged(self.repository)
        self.working_tree.calls = []
        self.callGetCVSDir()
        self.assertEqual(self.working_tree.calls, [
            # re-checkout, we want to preserve the catalog!
            ('cvsReCheckOut', self.repository),
            ('updateCscvsCache',),
            ('cscvsCvsTree',)])

    def testModifiedTree(self):
        # if the cvs path exists, has the correct repository but the tree has
        # changes: CVSStrategy.getCVSDir recheckouts the tree and updates the
        # cache.
        self.working_tree.cvsCheckOut(self.repository)
        self.working_tree._tree_has_changes = True
        assert self.working_tree.cvsTreeHasChanges()
        self.working_tree.calls = []
        self.callGetCVSDir()
        self.assertEqual(self.working_tree.calls, [
            # re-checkout, we want to preserve the catalog!
            ('cvsReCheckOut', self.repository),
            ('updateCscvsCache',),
            ('cscvsCvsTree',)])

    def testExistingCheckout(self):
        # if the cvs path exists, has the correct repository, and the tree has
        # no change: CVSStrategy.getCVSDir updates  the tree and the cache.
        self.working_tree.cvsCheckOut(self.repository)
        self.working_tree.calls = []
        self.callGetCVSDir()
        self.assertEqual(self.working_tree.calls, [
            # re-checkout, we want to preserve the catalog!
            ('cvsUpdate',),
            ('updateCscvsCache',),
            ('cscvsCvsTree',)])


testutil.register(__name__)
