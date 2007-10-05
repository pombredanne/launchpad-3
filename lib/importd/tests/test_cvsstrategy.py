# Copyright 2005-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import shutil

from bzrlib.branch import Branch
from bzrlib.urlutils import local_path_to_url
import CVS

from canonical.database.sqlbase import rollback
from importd import JobStrategy
from importd.bzrmanager import BzrManager
from importd.tests import testutil, helpers
from importd.tests.test_bzrmanager import ProductSeriesHelper


class CvsJobHelper(helpers.SimpleJobHelper):
    """Job factory for CVSStrategy test cases."""

    def setUp(self):
        helpers.SimpleJobHelper.setUp(self)
        self.cvsroot = self.sandbox.join('cvsrepo')
        self.cvsmodule = 'test'

    def makeJob(self):
        job = helpers.SimpleJobHelper.makeJob(self)
        job.RCS = "CVS"
        job.TYPE = "sync"
        job.repository = self.cvsroot
        job.module = self.cvsmodule
        job.branchfrom="MAIN"
        return job


class CscvsCvsHelper:
    """Helper for integration tests with cscvs for CVS functionality."""

    sourcefile_data = {
        'import': 'import\n',
        'commit-1': 'change 1\n',
        'commit-2': 'change 2\n',
        }
    """Contents of the CVS source file in successive revisions."""

    def __init__(self, sandbox, job_helper):
        self.sandbox = sandbox
        self.job_helper = job_helper

    def setUp(self):
        self.cvsroot = self.job_helper.cvsroot
        self.cvsmodule = self.job_helper.cvsmodule
        self.cvstreedir = self.sandbox.join('cvstree')
        self.cvsrepo = None

    def tearDown(self):
        pass

    def writeSourceFile(self, data):
        aFile = open(os.path.join(self.cvstreedir, 'file1'), 'w')
        aFile.write(data)
        aFile.close()

    def setUpCvsImport(self):
        """Setup a CVS repository with just the initial revision."""
        logger = testutil.makeSilentLogger()
        repo = CVS.init(self.cvsroot, logger)
        self.cvsrepo = repo
        sourcedir = self.cvstreedir
        os.mkdir(sourcedir)
        self.writeSourceFile(self.sourcefile_data['import'])
        repo.Import(module=self.cvsmodule, log="import", vendor="vendor",
                    release=['release'], dir=sourcedir)
        shutil.rmtree(sourcedir)

    def setUpCvsRevision(self, number=1):
        """Create a revision in the repository created by setUpCvsImport."""
        sourcedir = self.cvstreedir
        self.cvsrepo.get(module=self.cvsmodule, dir=sourcedir)
        self.writeSourceFile(self.sourcefile_data['commit-%d' % number])
        cvsTree = CVS.tree(sourcedir)
        cvsTree.commit(log="change %d" % number)
        shutil.rmtree(sourcedir)


class CscvsCvsTestCase(helpers.JobTestCase):
    """Base class for tests using cscvs for CVS imports."""

    jobHelperType = CvsJobHelper

    def setUp(self):
        helpers.JobTestCase.setUp(self)
        self.cscvs_helper = CscvsCvsHelper(self.sandbox, self.job_helper)
        self.cscvs_helper.setUp()

    def tearDown(self):
        self.cscvs_helper.tearDown()
        helpers.JobTestCase.tearDown(self)


class CvsStrategyTestCase(CscvsCvsTestCase):
    """Common base for CVSStrategy test case classes."""

    def setUp(self):
        CscvsCvsTestCase.setUp(self)
        self.job = self.job_helper.makeJob()
        self.logger = testutil.makeSilentLogger()
        self.cvspath = self.sandbox.join('series-0000002a', 'cvsworking')
        self.strategy = self.makeStrategy()

    def makeStrategy(self):
        job = self.job
        strategy = JobStrategy.CVSStrategy()
        strategy.aJob = job
        strategy.logger = self.logger
        return strategy

    def assertFile(self, path, data=None):
        """Check existence and optionally contents of a file.

        If the `data` parameter is not supplied, only check file existence.

        :param path: name of the file to check.
        :param data: expected content of the file.
        """
        self.assertTrue(os.path.exists(path))
        if data is None:
            return
        aFile = open(path)
        try:
            read_data = aFile.read()
        finally:
            aFile.close()
        self.assertEqual(read_data, data)

    def assertSourceFile(self, revision):
        """Compare the contents of the source file to the expected value.

        :param revision: revision of the sourcefile to expect.
        """
        path = os.path.join(self.cvspath, 'file1')
        data = self.cscvs_helper.sourcefile_data[revision]
        self.assertFile(path, data)

    def writeSourceFile(self, data):
        """Change the contents of the source file.

        :param data: data to write to the source file.
        """
        aFile = open(os.path.join(self.cvspath, 'file1'), 'w')
        aFile.write(data)
        aFile.close()


class TestCvsStrategy(CvsStrategyTestCase):
    """Unit tests for CVSStrategy."""

    def setUp(self):
        CvsStrategyTestCase.setUp(self)

    def testGetCvsDirPath(self):
        # CVSStrategy.getCvsDirPath is consistent with self.cvspath
        cvspath = self.strategy.getCVSDirPath(self.job, self.sandbox.path)
        self.assertEqual(cvspath, self.cvspath)

    def testSyncArgsSanityChecks(self):
        # XXX David Allouche 2006-06-06:
        #  I am not sure what these tests are for
        strategy = self.strategy
        logger = self.logger
        self.assertRaises(AssertionError, strategy.sync, None, ".", None)
        self.assertRaises(AssertionError, strategy.sync, ".", None, None)
        self.assertRaises(AssertionError, strategy.sync, None, None, logger)


class SilentBzrManager(BzrManager):
    """BzrManager which is silent by default.

    That is useful to keep the test runner's output clean.
    """

    def __init__(self, job):
        BzrManager.__init__(self, job)
        self.silent = True


class TestCvsStrategyBzr(CvsStrategyTestCase):

    def setUp(self):
        CvsStrategyTestCase.setUp(self)
        self.job.targetManagerType = SilentBzrManager
        self.job.working_root = self.sandbox.path
        push_prefix = self.job.push_prefix
        os.mkdir(push_prefix)
        self.push_prefix = self.job.push_prefix = local_path_to_url(push_prefix)
        self.utilities_helper = helpers.ZopelessUtilitiesHelper()
        self.utilities_helper.setUp()
        self.series_helper = ProductSeriesHelper()
        self.series_helper.setUp()
        self.series_helper.setUpSeries()
        self.job.seriesID = self.series_helper.series.id
        self.saved_dbname = os.environ.get('LP_DBNAME')
        os.environ['LP_DBNAME'] = 'launchpad_ftest'

    def tearDown(self):
        if self.saved_dbname is None:
            del os.environ['LP_DBNAME']
        else:
            os.environ['LP_DBNAME'] = self.saved_dbname
        self.series_helper.tearDown()
        self.utilities_helper.tearDown()
        CvsStrategyTestCase.tearDown(self)

    def localRevno(self):
        workingdir = self.sandbox.join('series-%08x' %
                                       self.series_helper.series.id)
        bzrworking = os.path.join(workingdir, 'bzrworking')
        return Branch.open(bzrworking).revno()

    def mirrorRevno(self):
        series = self.series_helper.getSeries()
        if series.import_branch is None:
            return None
        mirror_path = self.mirrorPath(series.import_branch.id)
        return Branch.open(mirror_path).revno()

    def assertRevnos(self, local, mirror):
        self.assertEqual(self.localRevno(), local)
        self.assertEqual(self.mirrorRevno(), mirror)

    def mirrorPath(self, branch_id):
        return os.path.join(self.job.push_prefix, '%08x' % branch_id)

    def testCvsImportAndSync(self):
        # Feature test for a CVS import to bzr
        # Check we can do an initial import from CVS.
        self.cscvs_helper.setUpCvsImport()
        self.cscvs_helper.setUpCvsRevision()
        self.makeStrategy().Import(self.job, self.sandbox.path, self.logger)
        self.assertRevnos(local=2, mirror=None)
        # After the import is successful, we run mirrorTarget to publish. We
        # need to rollback to see the database change made in a subprocess by
        # mirrorTarget
        self.job.mirrorTarget(self.sandbox.path, self.logger)
        rollback()
        self.assertRevnos(local=2, mirror=2)
        # Then we run the first sync, which finds nothing new
        self.makeStrategy().sync(self.job, self.sandbox.path, self.logger)
        self.assertRevnos(local=2, mirror=2)
        # Then something happens on the upstream repository, and we sync again
        self.cscvs_helper.setUpCvsRevision(2)
        self.makeStrategy().sync(self.job, self.sandbox.path, self.logger)
        self.assertRevnos(local=3, mirror=2)
        # Finally the synced import is published
        self.job.mirrorTarget(self.sandbox.path, self.logger)
        self.assertRevnos(local=3, mirror=3)


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
        # TODO: break this test into smaller more focused tests (bug 49694)
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
    # command must be deleted and the exception must be passed up. (bug 49693)
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
        # TODO: break this test into smaller more focused tests (bug 49694)
        # -- David Allouche 2006-06-06

        # CvsWorkingTree.cvsReCheckOut fails if there is no checkout
        self.assertRaises(AssertionError,
                          self.working_tree.cvsReCheckOut, self.repository)
        # Set up a checkout without catalog
        self.setUpCvsImport()
        self.working_tree.cvsCheckOut(self.repository)
        # CvsWorkingTree.cvsReCheckout fails if there is no catalog
        self.assertRaises(AssertionError,
                          self.working_tree.cvsReCheckOut, self.repository)
        # Setup a working tree with a fake catalog and source changes
        self.assertSourceFile('import')
        self.assertEqual(self.working_tree.cvsTreeHasChanges(), False)
        self.writeSourceFile('changed data\n')
        self.assertEqual(self.working_tree.cvsTreeHasChanges(), True)
        self.writeCatalog('Magic Cookie!\n')
        self.assertCatalog('Magic Cookie!\n')
        # CvsWorkingTree.cvsReCheckOut reverts source changes and preserves the
        # catalog.
        self.working_tree.cvsReCheckOut(self.repository)
        self.assertSourceFile('import')
        self.assertEqual(self.working_tree.cvsTreeHasChanges(), False)
        self.assertCatalog('Magic Cookie!\n')
        # XXX: David Allouche 2005-05-31: 
        # would also need to check that cvsReCheckOut uses the provided
        # repository and not the old repository, and that the old checkout is
        # untouched in case of failure, but it looks like it would be
        # complicated to implement in the fake environment.

    def testRepositoryHasChanged(self):
        # XXX: David Allouche 2006-06-06 bug=49694:
        # break this test into smaller more focused tests.

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
        changed_repo = self.makeCvsRepository(changed_cvsroot)
        has_changed = self.working_tree.repositoryHasChanged(changed_repo)
        self.assertEqual(has_changed, True)
        # CVSStrategy._repositoryHasChanged raises AssertionError if the
        # job.module and the tree module are different, regardless of the the
        # repository
        self.working_tree._job.module = 'changed'
        self.assertRaises(AssertionError,
            self.working_tree.repositoryHasChanged, self.repository)
        self.assertRaises(AssertionError,
            self.working_tree.repositoryHasChanged, changed_repo)

    def testUpdateCscvsCache(self):
        # TODO: break this test into smaller more focused tests (bug 49694)
        # -- David Allouche 2006-06-06

        # CvsWorkingTree.updateCscvsCache fails if there is no checkout
        self.assertRaises(AssertionError, self.working_tree.updateCscvsCache)
        self.job.working_root = self.sandbox.path
        # CvsWorkingTree.updatesCscvsCache creates the cscvs cache.
        # We need to create the import target here because updateCscvsCache
        # depends on it for log scanning. That saves separating creation of
        # catalog for new imports and for existing imports.
        self.setUpCvsImport()
        self.working_tree.cvsCheckOut(self.repository)
        target_manager = self.job.makeTargetManager()
        target_manager.createImportTarget(self.sandbox.join('series-0000002a'))
        self.working_tree.updateCscvsCache()
        self.assertCatalog()
        self.assertCatalogMainLength(2)
        # CvsWorkingTree.updateCscvsCache updates the cscvs cache
        self.setUpCvsRevision()
        self.working_tree.cvsUpdate()
        self.assertCatalogMainLength(2)
        self.working_tree.updateCscvsCache()
        self.assertCatalogMainLength(3)

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
        self.job.getWorkingDir(self.sandbox.path) # create parents of cvspath
        self.working_tree = JobStrategy.CvsWorkingTree(
            self.job, self.cvspath, self.logger)
        self.repository = self.makeCvsRepository(self.job.repository)

    def makeCvsRepository(self, cvsroot):
        return CVS.Repository(cvsroot, self.logger)

    def setUpCvsImport(self):
        self.cscvs_helper.setUpCvsImport()

    def setUpCvsRevision(self):
        self.cscvs_helper.setUpCvsRevision()

    def _catalogPath(self):
        return os.path.join(self.cvspath, "CVS", "Catalog.sqlite")

    def writeCatalog(self, data):
        aFile = open(self._catalogPath(), 'w')
        aFile.write(data)
        aFile.close()

    def assertCatalog(self, data=None):
        """Check existence and optionally contents of the cscvs catalog.

        :param data: expected content of the catalog file. If not supplied,
            only check file existence.
        """
        self.assertFile(self._catalogPath(), data)

    def assertCatalogMainLength(self, length):
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
        self.job.getWorkingDir(self.sandbox.path) # create parents of cvspath
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

    def writeCatalog(self, data):
        assert self.working_tree._has_tree
        self.working_tree._has_catalog = True
        self.working_tree._catalog_data = data

    def assertCatalog(self, data=None):
        self.assertNotEqual(self.working_tree._has_catalog, None)
        if data is None:
            return
        # catalog_data is not None only if it was set with writeCatalog
        # and only then the contents are known and can be checked
        assert self.working_tree._catalog_data is not None
        self.assertEqual(self.working_tree._catalog_data, data)

    def assertCatalogMainLength(self, length):
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
        self._catalog_data = None
        self._catalog_main_length = None
        self._tree_repository = None
        self._tree_module = None
        self._tree_revision = None
        self._tree_has_changes = None

    def cvsCheckOut(self, repository):
        self.calls.append(('cvsCheckOut', repository))
        assert not self._has_tree
        self._has_tree = True
        self._tree_revision = repository._revision
        self._tree_repository = repository
        self._tree_module = self._job.module
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
        assert self._has_catalog
        self._tree_revision = repository._revision
        self._tree_repository = repository
        self._tree_module = self._job.module
        self._tree_has_changes = False

    def repositoryHasChanged(self, repository):
        assert self._has_tree
        assert self._tree_module == self._job.module
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
        value = self.strategy.getCVSDir(self.job, self.sandbox.path)
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
        self.working_tree.updateCscvsCache()
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
        self.working_tree.updateCscvsCache()
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
