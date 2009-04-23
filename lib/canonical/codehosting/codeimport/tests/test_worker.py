# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the code import worker."""

__metaclass__ = type

import logging
import os
import shutil
import subprocess
import tempfile
import time
import unittest

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir, BzrDirFormat, format_registry
from bzrlib.errors import NoSuchFile
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport import get_transport
from bzrlib.upgrade import upgrade
from bzrlib.urlutils import join as urljoin

from canonical.cachedproperty import cachedproperty
from canonical.codehosting import load_optional_plugin
from canonical.codehosting.codeimport.worker import (
    BazaarBranchStore, CSCVSImportWorker, ForeignTreeStore, ImportWorker,
    PullingImportWorker, get_default_bazaar_branch_store,
    get_default_foreign_tree_store)
from canonical.codehosting.codeimport.tests.servers import (
    CVSServer, GitServer, SubversionServer)
from canonical.codehosting.tests.helpers import (
    create_branch_with_one_revision)
from canonical.config import config
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import BaseLayer

import pysvn


default_format = BzrDirFormat.get_default_format()


class WorkerTest(TestCaseWithTransport):
    """Base test case for things that test the code import worker.

    Provides Bazaar testing features, access to Launchpad objects and
    factories for some code import objects.
    """

    layer = BaseLayer

    def assertDirectoryTreesEqual(self, directory1, directory2):
        """Assert that `directory1` has the same structure as `directory2`.

        That is, assert that all of the files and directories beneath
        `directory1` are laid out in the same way as `directory2`.
        """
        def list_files(directory):
            for path, ignored, ignored in os.walk(directory):
                yield path[len(directory):]
        self.assertEqual(
            sorted(list_files(directory1)), sorted(list_files(directory2)))

    @cachedproperty
    def factory(self):
        return LaunchpadObjectFactory()

    def makeTemporaryDirectory(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        return directory


class TestBazaarBranchStore(WorkerTest):
    """Tests for `BazaarBranchStore`."""

    def setUp(self):
        super(TestBazaarBranchStore, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.arbitrary_branch_id = 10

    def makeBranchStore(self):
        return BazaarBranchStore(self.get_transport())

    def test_defaultStore(self):
        # The default store is at config.codeimport.bazaar_branch_store.
        store = get_default_bazaar_branch_store()
        self.assertEqual(
            store.transport.base.rstrip('/'),
            config.codeimport.bazaar_branch_store.rstrip('/'))

    def test_getNewBranch(self):
        # If there's no Bazaar branch of this id, then pull creates a new
        # Bazaar working tree.
        store = self.makeBranchStore()
        bzr_working_tree = store.pull(
            self.arbitrary_branch_id, self.temp_dir, default_format)
        self.assertEqual([], bzr_working_tree.branch.revision_history())

    def test_pushBranchThenPull(self):
        # After we've pushed up a branch to the store, we can then pull it
        # from the store.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.arbitrary_branch_id, tree, default_format)
        new_tree = store.pull(
            self.arbitrary_branch_id, self.temp_dir, default_format)
        self.assertEqual(
            tree.branch.last_revision(), new_tree.branch.last_revision())

    def test_pullUpgradesFormat(self):
        # A branch should always be in the most up-to-date format before a
        # pull is performed.
        store = self.makeBranchStore()
        target_url = store._getMirrorURL(self.arbitrary_branch_id)
        knit_format = format_registry.get('knit')()
        tree = create_branch_with_one_revision(target_url, format=knit_format)
        default_format = BzrDirFormat.get_default_format()

        # The fetched branch is in the default format.
        new_tree = store.pull(
            self.arbitrary_branch_id, self.temp_dir, default_format)
        self.assertEqual(
            default_format, new_tree.branch.bzrdir._format)

        # In addition. the remote branch has been upgraded as well.
        new_branch = Branch.open(target_url)
        self.assertEqual(
            default_format.get_branch_format(), new_branch._format)

    def test_pullUpgradesFormatWithBackupDirPresent(self):
        # pull can upgrade the remote branch even if there is a backup.bzr
        # directory from a previous upgrade.
        store = self.makeBranchStore()
        target_url = store._getMirrorURL(self.arbitrary_branch_id)
        knit_format = format_registry.get('knit')()
        tree = create_branch_with_one_revision(target_url, format=knit_format)
        upgrade(target_url, format_registry.get('dirstate-tags')())
        self.failUnless(get_transport(target_url).has('backup.bzr'))
        default_format = BzrDirFormat.get_default_format()

        # The fetched branch is in the default format.
        new_tree = store.pull(
            self.arbitrary_branch_id, self.temp_dir, default_format)
        self.assertEqual(
            default_format, new_tree.branch.bzrdir._format)

        # In addition. the remote branch has been upgraded as well.
        new_branch = Branch.open(target_url)
        self.assertEqual(
            default_format.get_branch_format(), new_branch._format)

    def test_pushTwiceThenPull(self):
        # We can push up a branch to the store twice and then pull it from the
        # store.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.arbitrary_branch_id, tree, default_format)
        store.push(self.arbitrary_branch_id, tree, default_format)
        new_tree = store.pull(
            self.arbitrary_branch_id, self.temp_dir, default_format)
        self.assertEqual(
            tree.branch.last_revision(), new_tree.branch.last_revision())

    def fetchBranch(self, from_url, target_path):
        """Pull a branch from `from_url` to `target_path`.

        This uses the Bazaar API for pulling a branch, and is used to test
        that `push` indeed pushes a branch to a specific location.

        :return: The working tree of the branch.
        """
        bzr_dir = BzrDir.open(from_url)
        bzr_dir.sprout(target_path)
        return BzrDir.open(target_path).open_workingtree()

    def test_makesDirectories(self):
        # push() tries to create the base directory of the branch store if it
        # doesn't already exist.
        store = BazaarBranchStore(self.get_transport('doesntexist'))
        tree = create_branch_with_one_revision('original')
        store.push(self.arbitrary_branch_id, tree, default_format)
        self.assertIsDirectory('doesntexist', self.get_transport())

    def test_storedLocation(self):
        # push() puts the branch in a directory named after the branch ID on
        # the BazaarBranchStore's transport.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.arbitrary_branch_id, tree, default_format)
        new_tree = self.fetchBranch(
            urljoin(store.transport.base, '%08x' % self.arbitrary_branch_id),
            'new_tree')
        self.assertEqual(
            tree.branch.last_revision(), new_tree.branch.last_revision())

    def test_sftpPrefix(self):
        # Since branches are mirrored by importd via sftp, _getMirrorURL must
        # support sftp urls. There was once a bug that made it incorrect with
        # sftp.
        sftp_prefix = 'sftp://example/base/'
        store = BazaarBranchStore(get_transport(sftp_prefix))
        self.assertEqual(
            store._getMirrorURL(self.arbitrary_branch_id),
            sftp_prefix + '%08x' % self.arbitrary_branch_id)

    def test_sftpPrefixNoSlash(self):
        # If the prefix has no trailing slash, one should be added. It's very
        # easy to forget a trailing slash in the importd configuration.
        sftp_prefix_noslash = 'sftp://example/base'
        store = BazaarBranchStore(get_transport(sftp_prefix_noslash))
        self.assertEqual(
            store._getMirrorURL(self.arbitrary_branch_id),
            sftp_prefix_noslash + '/' + '%08x' % self.arbitrary_branch_id)


class MockForeignWorkingTree:
    """Working tree that records calls to checkout and update."""

    def __init__(self, local_path):
        self.local_path = local_path
        self.log = []

    def checkout(self):
        self.log.append('checkout')

    def update(self):
        self.log.append('update')


class TestForeignTreeStore(WorkerTest):
    """Tests for the `ForeignTreeStore` object."""

    def assertCheckedOut(self, tree):
        self.assertEqual(['checkout'], tree.log)

    def assertUpdated(self, tree):
        self.assertEqual(['update'], tree.log)

    def setUp(self):
        """Set up a code import for an SVN working tree."""
        super(TestForeignTreeStore, self).setUp()
        self.source_details = self.factory.makeCodeImportSourceDetails()
        self.temp_dir = self.makeTemporaryDirectory()

    def makeForeignTreeStore(self, transport=None):
        """Make a foreign tree store.

        The store is in a different directory to the local working directory.
        """
        def _getForeignTree(source_details, target_path):
            return MockForeignWorkingTree(target_path)
        if transport is None:
            transport = self.get_transport('remote')
        store = ForeignTreeStore(transport)
        store._getForeignTree = _getForeignTree
        return store

    def test_getForeignTreeSubversion(self):
        # _getForeignTree() returns a Subversion working tree for Subversion
        # code imports.
        store = ForeignTreeStore(None)
        svn_branch_url = self.factory.getUniqueURL()
        source_details = self.factory.makeCodeImportSourceDetails(
            rcstype='svn')
        working_tree = store._getForeignTree(source_details, 'path')
        self.assertIsSameRealPath(working_tree.local_path, 'path')
        self.assertEqual(
            working_tree.remote_url, source_details.svn_branch_url)

    def test_getForeignTreeCVS(self):
        # _getForeignTree() returns a CVS working tree for CVS code imports.
        store = ForeignTreeStore(None)
        source_details = self.factory.makeCodeImportSourceDetails(
            rcstype='cvs')
        working_tree = store._getForeignTree(source_details, 'path')
        self.assertIsSameRealPath(working_tree.local_path, 'path')
        self.assertEqual(working_tree.root, source_details.cvs_root)
        self.assertEqual(working_tree.module, source_details.cvs_module)

    def test_defaultStore(self):
        # The default store is at config.codeimport.foreign_tree_store.
        store = get_default_foreign_tree_store()
        self.assertEqual(
            store.transport.base.rstrip('/'),
            config.codeimport.foreign_tree_store.rstrip('/'))

    def test_getNewWorkingTree(self):
        # If the foreign tree store doesn't have an archive of the foreign
        # tree, then fetching the tree actually pulls in from the original
        # site.
        store = self.makeForeignTreeStore()
        tree = store.fetchFromSource(self.source_details, self.temp_dir)
        self.assertCheckedOut(tree)

    def test_archiveTree(self):
        # Once we have a foreign working tree, we can archive it so that we
        # can retrieve it more reliably in the future.
        store = self.makeForeignTreeStore()
        foreign_tree = store.fetchFromSource(
            self.source_details, self.temp_dir)
        store.archive(self.source_details, foreign_tree)
        self.assertTrue(
            store.transport.has(
                '%08x.tar.gz' % self.source_details.branch_id),
            "Couldn't find '%08x.tar.gz'" % self.source_details.branch_id)

    def test_makeDirectories(self):
        # archive() tries to create the base directory of the foreign tree
        # store if it doesn't already exist.
        store = self.makeForeignTreeStore(self.get_transport('doesntexist'))
        foreign_tree = store.fetchFromSource(
            self.source_details, self.temp_dir)
        store.archive(self.source_details, foreign_tree)
        self.assertIsDirectory('doesntexist', self.get_transport())

    def test_fetchFromArchiveFailure(self):
        # If a tree has not been archived yet, but we try to retrieve it from
        # the archive, we get a NoSuchFile error.
        store = self.makeForeignTreeStore()
        self.assertRaises(
            NoSuchFile,
            store.fetchFromArchive, self.source_details, self.temp_dir)

    def test_fetchFromArchive(self):
        # After archiving a tree, we can retrieve it from the store -- the
        # tarball gets downloaded and extracted.
        store = self.makeForeignTreeStore()
        foreign_tree = store.fetchFromSource(
            self.source_details, self.temp_dir)
        store.archive(self.source_details, foreign_tree)
        new_temp_dir = self.makeTemporaryDirectory()
        foreign_tree2 = store.fetchFromArchive(
            self.source_details, new_temp_dir)
        self.assertEqual(new_temp_dir, foreign_tree2.local_path)
        self.assertDirectoryTreesEqual(self.temp_dir, new_temp_dir)

    def test_fetchFromArchiveUpdates(self):
        # The local working tree is updated with changes from the remote
        # branch after it has been fetched from the archive.
        store = self.makeForeignTreeStore()
        foreign_tree = store.fetchFromSource(
            self.source_details, self.temp_dir)
        store.archive(self.source_details, foreign_tree)
        new_temp_dir = self.makeTemporaryDirectory()
        foreign_tree2 = store.fetchFromArchive(
            self.source_details, new_temp_dir)
        self.assertUpdated(foreign_tree2)


class FakeForeignTreeStore(ForeignTreeStore):
    """A ForeignTreeStore that always fetches fake foreign trees."""

    def __init__(self):
        ForeignTreeStore.__init__(self, None)

    def fetch(self, source_details, target_path):
        return MockForeignWorkingTree(target_path)


class TestWorkerCore(WorkerTest):
    """Tests for the core (VCS-independent) part of the code import worker."""

    def setUp(self):
        WorkerTest.setUp(self)
        self.source_details = self.factory.makeCodeImportSourceDetails()

    def makeBazaarBranchStore(self):
        """Make a Bazaar branch store."""
        return BazaarBranchStore(self.get_transport('bazaar_branches'))

    def makeImportWorker(self):
        """Make an ImportWorker that only uses fake branches."""
        return ImportWorker(
            self.source_details, self.makeBazaarBranchStore(),
            logging.getLogger("silent"))

    def test_construct(self):
        # When we construct an ImportWorker, it has a CodeImportSourceDetails
        # object.
        worker = self.makeImportWorker()
        self.assertEqual(self.source_details, worker.source_details)

    def test_getBazaarWorkingTreeMakesEmptyTree(self):
        # getBazaarWorkingTree returns a brand-new working tree for an initial
        # import.
        worker = self.makeImportWorker()
        bzr_working_tree = worker.getBazaarWorkingTree()
        self.assertEqual([], bzr_working_tree.branch.revision_history())

    def test_bazaarWorkingTreeLocation(self):
        # getBazaarWorkingTree makes the working tree under the current
        # working directory.
        worker = self.makeImportWorker()
        bzr_working_tree = worker.getBazaarWorkingTree()
        self.assertIsSameRealPath(
            os.path.abspath(worker.BZR_WORKING_TREE_PATH),
            os.path.abspath(bzr_working_tree.basedir))


class TestCSCVSWorker(WorkerTest):
    """Tests for methods specific to CSCVSImportWorker."""

    def setUp(self):
        WorkerTest.setUp(self)
        self.source_details = self.factory.makeCodeImportSourceDetails()

    def makeImportWorker(self):
        """Make an ImportWorker that only uses fake foreign trees."""
        return CSCVSImportWorker(
            self.source_details, FakeForeignTreeStore(),
            None, logging.getLogger("silent"))

    def test_getForeignTree(self):
        # getForeignTree returns an object that represents the 'foreign'
        # branch (i.e. a CVS or Subversion branch).
        worker = self.makeImportWorker()
        working_tree = worker.getForeignTree()
        self.assertIsSameRealPath(
            os.path.abspath(worker.FOREIGN_WORKING_TREE_PATH),
            working_tree.local_path)


def clean_up_default_stores_for_import(source_details):
    """Clean up the default branch and foreign tree stores for an import.

    This checks for an existing branch and/or foreign tree tarball
    corresponding to the passed in import and deletes them if they
    are found.

    If there are tarballs or branches in the default stores that
    might conflict with working on our job, life gets very, very
    confusing.

    :source_details: A `CodeImportSourceDetails` describing the import.
    """
    treestore = get_default_foreign_tree_store()
    tree_transport = treestore.transport
    archive_name = treestore._getTarballName(source_details.branch_id)
    if tree_transport.has(archive_name):
        tree_transport.delete(archive_name)
    branchstore = get_default_bazaar_branch_store()
    branch_transport = branchstore.transport
    branch_name = '%08x' % source_details.branch_id
    if branchstore.transport.has(branch_name):
        branchstore.transport.delete_tree(branch_name)


class TestActualImportMixin:
    """Mixin for tests that check the actual importing."""

    def setUpImport(self):
        """Set up the objects required for an import.

        This means a BazaarBranchStore, CodeImport and a CodeImportJob.
        """
        self.bazaar_store = BazaarBranchStore(
            self.get_transport('bazaar_store'))
        self.source_details = self.makeSourceDetails(
            'trunk', [('README', 'Original contents')])

    def makeImportWorker(self):
        """Make a new `ImportWorker`.

        Override this in your subclass.
        """
        raise NotImplementedError(
            "Override this with a VCS-specific implementation.")

    def commitInForeignTree(self, foreign_tree):
        """Commit a single revision to `foreign_tree`.

        Override this in your subclass.
        """
        raise NotImplementedError(
            "Override this with a VCS-specific implementation.")

    def makeSourceDetails(self, module_name, files):
        """Make a `CodeImportSourceDetails` that points to a real repository.

        Override this in your subclass.
        """
        raise NotImplementedError(
            "Override this with a VCS-specific implementation.")

    def getStoredBazaarBranch(self, worker):
        """Get the Bazaar branch 'worker' stored into its BazaarBranchStore.
        """
        branch_url = worker.bazaar_branch_store._getMirrorURL(
            worker.source_details.branch_id)
        return Branch.open(branch_url)

    def test_import(self):
        # Running the worker on a branch that hasn't been imported yet imports
        # the branch.
        worker = self.makeImportWorker()
        worker.run()
        branch = self.getStoredBazaarBranch(worker)
        self.assertEqual(
            self.foreign_commit_count, len(branch.revision_history()))

    def test_sync(self):
        # Do an import.
        worker = self.makeImportWorker()
        worker.run()
        branch = self.getStoredBazaarBranch(worker)
        self.assertEqual(
            self.foreign_commit_count, len(branch.revision_history()))

        # Change the remote branch.

        tree_dir = self.makeTemporaryDirectory()
        # This is pretty gross, but it works: the call to worker.run() will
        # chdir() again to the worker's scratch directory, and in any case the
        # tests subclass bzrlib's TestCaseInTempdir, so the directory will be
        # restored at the end of the test.
        os.chdir(tree_dir)
        if isinstance(worker, CSCVSImportWorker):
            foreign_tree = worker.foreign_tree_store.fetch(
                worker.source_details, tree_dir)
        else:
            foreign_tree = None
        self.commitInForeignTree(foreign_tree)

        # Run the same worker again.
        worker.run()

        # Check that the new revisions are in the Bazaar branch.
        branch = self.getStoredBazaarBranch(worker)
        self.assertEqual(
            self.foreign_commit_count, len(branch.revision_history()))

    def test_import_script(self):
        # Like test_import, but using the code-import-worker.py script
        # to perform the import.

        clean_up_default_stores_for_import(self.source_details)

        script_path = os.path.join(
            config.root, 'scripts', 'code-import-worker.py')
        retcode = subprocess.call(
            [script_path, '-qqq'] + self.source_details.asArguments())
        self.assertEqual(retcode, 0)

        self.addCleanup(
            lambda : clean_up_default_stores_for_import(self.source_details))

        tree_path = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(tree_path))

        branch_url = get_default_bazaar_branch_store()._getMirrorURL(
            self.source_details.branch_id)
        branch = Branch.open(branch_url)

        self.assertEqual(
            self.foreign_commit_count, len(branch.revision_history()))


class CSCVSActualImportMixin(TestActualImportMixin):

    def setUpImport(self):
        """Set up the objects required for an import.

        This sets up a ForeignTreeStore in addition to what
        TestActualImportMixin.setUpImport does.
        """
        TestActualImportMixin.setUpImport(self)
        self.foreign_store = ForeignTreeStore(
            self.get_transport('foreign_store'))

    def makeImportWorker(self):
        """Make a new `ImportWorker`."""
        return CSCVSImportWorker(
            self.source_details, self.foreign_store, self.bazaar_store,
            logging.getLogger())


class TestCVSImport(WorkerTest, CSCVSActualImportMixin):
    """Tests for the worker importing and syncing a CVS module."""

    def setUp(self):
        super(TestCVSImport, self).setUp()
        self.setUpImport()
        self.foreign_commit_count = 0

    def commitInForeignTree(self, foreign_tree):
        # If you write to a file in the same second as the previous commit,
        # CVS will not think that it has changed.
        time.sleep(1)
        self.build_tree_contents(
            [(os.path.join(foreign_tree.local_path, 'README'),
              'New content')])
        foreign_tree.commit()
        self.foreign_commit_count += 1

    def makeSourceDetails(self, module_name, files):
        """Make a CVS `CodeImportSourceDetails` pointing at a real CVS repo.
        """
        cvs_server = CVSServer(self.makeTemporaryDirectory())
        cvs_server.setUp()
        self.addCleanup(cvs_server.tearDown)

        cvs_server.makeModule('trunk', [('README', 'original\n')])

        self.foreign_commit_count = 2

        return self.factory.makeCodeImportSourceDetails(
            rcstype='cvs', cvs_root=cvs_server.getRoot(), cvs_module='trunk')


class TestSubversionImport(WorkerTest, CSCVSActualImportMixin):
    """Tests for the worker importing and syncing a Subversion branch."""

    def setUp(self):
        WorkerTest.setUp(self)
        self.setUpImport()

    def commitInForeignTree(self, foreign_tree):
        """Change the foreign tree, generating exactly one commit."""
        svn_url = foreign_tree.remote_url
        client = pysvn.Client()
        client.checkout(svn_url, 'working_tree')
        file = open('working_tree/newfile', 'w')
        file.write('No real content\n')
        file.close()
        client.add('working_tree/newfile')
        client.checkin('working_tree', 'Add a file', recurse=True)
        self.foreign_commit_count += 1
        shutil.rmtree('working_tree')

    def makeSourceDetails(self, branch_name, files):
        """Make a SVN `CodeImportSourceDetails` pointing at a real SVN repo.
        """
        svn_server = SubversionServer(self.makeTemporaryDirectory())
        svn_server.setUp()
        self.addCleanup(svn_server.tearDown)

        svn_branch_url = svn_server.makeBranch(branch_name, files)
        self.foreign_commit_count = 2

        return self.factory.makeCodeImportSourceDetails(
            rcstype='svn', svn_branch_url=svn_branch_url)


class TestGitImport(WorkerTest, TestActualImportMixin):

    def setUp(self):
        super(TestGitImport, self).setUp()
        load_optional_plugin('git')
        self.setUpImport()

    def makeImportWorker(self):
        """Make a new `ImportWorker`."""
        return PullingImportWorker(
            self.source_details, self.bazaar_store, logging.getLogger())

    def commitInForeignTree(self, foreign_tree):
        """Change the foreign tree, generating exactly one commit."""
        from bzrlib.plugins.git.tests import run_git
        wd = os.getcwd()
        os.chdir(self.repository_path)
        try:
            run_git('config', 'user.name', 'Joe Random Hacker')
            run_git('commit', '-m', 'dsadas')
            self.foreign_commit_count += 1
        finally:
            os.chdir(wd)

    def makeSourceDetails(self, branch_name, files):
        """Make a Git `CodeImportSourceDetails` pointing at a real Git repo.
        """
        self.repository_path = self.makeTemporaryDirectory()
        git_server = GitServer(self.repository_path)
        git_server.setUp()
        self.addCleanup(git_server.tearDown)

        git_server.makeRepo(files)
        self.foreign_commit_count = 1

        return self.factory.makeCodeImportSourceDetails(
            rcstype='git', git_repo_url=self.repository_path)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
