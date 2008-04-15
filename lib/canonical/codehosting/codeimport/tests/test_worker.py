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

from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NoSuchFile
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport import get_transport
from bzrlib.urlutils import join as urljoin

from canonical.cachedproperty import cachedproperty
from canonical.codehosting import get_rocketfuel_root
from canonical.codehosting.codeimport.worker import (
    BazaarBranchStore, CodeImportSourceDetails, ForeignTreeStore,
    ImportWorker, get_default_bazaar_branch_store,
    get_default_foreign_tree_store)
from canonical.codehosting.codeimport.tests.test_foreigntree import (
    CVSServer, SubversionServer)
from canonical.codehosting.tests.helpers import (
    create_branch_with_one_revision)
from canonical.config import config
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import BaseLayer

import pysvn


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
            list(list_files(directory1)), list(list_files(directory2)))

    @cachedproperty
    def factory(self):
        return LaunchpadObjectFactory()

    def makeTemporaryDirectory(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(directory))
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
        bzr_working_tree = store.pull(self.arbitrary_branch_id, self.temp_dir)
        self.assertEqual([], bzr_working_tree.branch.revision_history())

    def test_pushBranchThenPull(self):
        # After we've pushed up a branch to the store, we can then pull it
        # from the store.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.arbitrary_branch_id, tree)
        new_tree = store.pull(self.arbitrary_branch_id, self.temp_dir)
        self.assertEqual(
            tree.branch.last_revision(), new_tree.branch.last_revision())

    def test_pushTwiceThenPull(self):
        # We can push up a branch to the store twice and then pull it from the
        # store.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.arbitrary_branch_id, tree)
        store.push(self.arbitrary_branch_id, tree)
        new_tree = store.pull(self.arbitrary_branch_id, self.temp_dir)
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
        store.push(self.arbitrary_branch_id, tree)
        self.assertIsDirectory('doesntexist', self.get_transport())

    def test_storedLocation(self):
        # push() puts the branch in a directory named after the branch ID on
        # the BazaarBranchStore's transport.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.arbitrary_branch_id, tree)
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
        self.source_details = CodeImportSourceDetails.fromArguments(
            ['123', 'svn', self.factory.getUniqueURL()])
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
        source_details = CodeImportSourceDetails.fromArguments(
            ['123', 'svn', self.factory.getUniqueURL()])
        working_tree = store._getForeignTree(source_details, 'path')
        self.assertIsSameRealPath(working_tree.local_path, 'path')
        self.assertEqual(
            working_tree.remote_url, source_details.svn_branch_url)

    def test_getForeignTreeCVS(self):
        # _getForeignTree() returns a CVS working tree for CVS code imports.
        store = ForeignTreeStore(None)
        source_details = CodeImportSourceDetails.fromArguments(
            ['123', 'cvs', 'root', 'module'])
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
        self.source_details = CodeImportSourceDetails.fromArguments(
            ['123', 'svn', self.factory.getUniqueURL()])

    def makeBazaarBranchStore(self):
        """Make a Bazaar branch store."""
        return BazaarBranchStore(self.get_transport('bazaar_branches'))

    def makeImportWorker(self):
        """Make an ImportWorker that only uses fake branches."""
        return ImportWorker(
            self.source_details, FakeForeignTreeStore(),
            self.makeBazaarBranchStore(),
            logging.getLogger("silent"))

    def test_construct(self):
        # When we construct an ImportWorker, it has a CodeImportSourceDetails
        # object and a working directory.
        worker = self.makeImportWorker()
        self.assertEqual(self.source_details, worker.source_details)
        self.assertEqual(True, os.path.isdir(worker.working_directory))

    def test_getBazaarWorkingTreeMakesEmptyTree(self):
        # getBazaarWorkingTree returns a brand-new working tree for an initial
        # import.
        worker = self.makeImportWorker()
        bzr_working_tree = worker.getBazaarWorkingTree()
        self.assertEqual([], bzr_working_tree.branch.revision_history())

    def test_bazaarWorkingTreeLocation(self):
        # getBazaarWorkingTree makes the working tree under the worker's
        # working directory.
        worker = self.makeImportWorker()
        bzr_working_tree = worker.getBazaarWorkingTree()
        self.assertIsSameRealPath(
            os.path.join(
                worker.working_directory, worker.BZR_WORKING_TREE_PATH),
            os.path.abspath(bzr_working_tree.basedir))

    def test_getForeignTree(self):
        # getForeignTree returns an object that represents the 'foreign'
        # branch (i.e. a CVS or Subversion branch).
        worker = self.makeImportWorker()
        branch = worker.getForeignTree()
        self.assertIsSameRealPath(
            os.path.join(
                worker.working_directory, worker.FOREIGN_WORKING_TREE_PATH),
            branch.local_path)


def clean_up_default_stores_for_import(source_details):
    """Clean up default branch and foreign tree stores for an import.

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

        This means a BazaarBranchStore, ForeignTreeStore, CodeImport and
        a CodeImportJob.
        """
        repository_path = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(repository_path))

        self.bazaar_store = BazaarBranchStore(
            self.get_transport('bazaar_store'))
        self.foreign_store = ForeignTreeStore(
            self.get_transport('foreign_store'))

        self.source_details = self.makeSourceDetails(
            repository_path, 'trunk', [('README', 'Original contents')])

    def commitInForeignTree(self, foreign_tree):
        """Commit a single revision to `foreign_tree`.

        Override this in your subclass.
        """
        raise NotImplementedError(
            "Override this with a VCS-specific implementation.")

    def makeSourceDetails(self, repository_path, module_name, files):
        """Make a `CodeImportSourceDetails` that points to a real repository.

        Override this in your subclass.
        """
        raise NotImplementedError(
            "Override this with a VCS-specific implementation.")

    def makeImportWorker(self):
        """Make a new `ImportWorker`."""
        return ImportWorker(
            self.source_details, self.foreign_store, self.bazaar_store,
            logging.getLogger())

    def test_import(self):
        # Running the worker on a branch that hasn't been imported yet imports
        # the branch.
        worker = self.makeImportWorker()
        worker.run()
        bazaar_tree = worker.getBazaarWorkingTree()
        # XXX: JonathanLange 2008-02-22: This assumes that the branch that we
        # are importing has two revisions. Looking at the test, it's not
        # obvious why we make this assumption, hence the XXX. The two
        # revisions are from 1) making the repository and 2) adding a file.
        # The name of this test smell is "Mystery Guest".
        self.assertEqual(2, len(bazaar_tree.branch.revision_history()))

    def test_sync(self):
        # Do an import.
        worker = self.makeImportWorker()
        worker.run()
        bazaar_tree = worker.getBazaarWorkingTree()
        self.assertEqual(2, len(bazaar_tree.branch.revision_history()))

        # Change the remote branch.
        foreign_tree = worker.getForeignTree()
        self.commitInForeignTree(foreign_tree)

        # Run the same worker again.
        worker.run()

        # Check that the new revisions are in the Bazaar branch.
        bazaar_tree = worker.getBazaarWorkingTree()
        self.assertEqual(3, len(bazaar_tree.branch.revision_history()))

    def test_import_script(self):
        # Like test_import, but using the code-import-worker.py script
        # to perform the import.

        clean_up_default_stores_for_import(self.source_details)

        script_path = os.path.join(
            get_rocketfuel_root(), 'scripts', 'code-import-worker.py')
        retcode = subprocess.call(
            [script_path, '-qqq'] + self.source_details.asArguments())
        self.assertEqual(retcode, 0)

        self.addCleanup(
            lambda : clean_up_default_stores_for_import(self.source_details))

        tree_path = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(tree_path))

        bazaar_tree = get_default_bazaar_branch_store().pull(
            self.source_details.branch_id, tree_path)

        self.assertEqual(2, len(bazaar_tree.branch.revision_history()))



class TestCVSImport(WorkerTest, TestActualImportMixin):
    """Tests for the worker importing and syncing a CVS module."""

    def setUp(self):
        super(TestCVSImport, self).setUp()
        self.setUpImport()

    def commitInForeignTree(self, foreign_tree):
        # If you write to a file in the same second as the previous commit,
        # CVS will not think that it has changed.
        time.sleep(1)
        self.build_tree_contents(
            [(os.path.join(foreign_tree.local_path, 'README'),
              'New content')])
        foreign_tree.commit()

    def makeSourceDetails(self, repository_path, module_name, files):
        """Make a CVS `CodeImportSourceDetails` pointing at a real CVS repo.
        """
        cvs_server = CVSServer(repository_path)
        cvs_server.setUp()
        self.addCleanup(cvs_server.tearDown)

        cvs_server.makeModule('trunk', [('README', 'original\n')])

        return CodeImportSourceDetails.fromArguments(
            ['123', 'cvs', cvs_server.getRoot(), 'trunk'])


class TestSubversionImport(WorkerTest, TestActualImportMixin):
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
        shutil.rmtree('working_tree')

    def makeSourceDetails(self, repository_path, branch_name, files):
        """Make a SVN `CodeImportSourceDetails` pointing at a real SVN repo.
        """
        svn_server = SubversionServer(repository_path)
        svn_server.setUp()
        self.addCleanup(svn_server.tearDown)

        svn_branch_url = svn_server.makeBranch(branch_name, files)
        return CodeImportSourceDetails.fromArguments(
            ['123', 'svn', svn_branch_url])

    def test_bazaarBranchStored(self):
        # The worker stores the Bazaar branch after it has imported the new
        # revisions.
        # XXX: JonathanLange 2008-02-22: This test ought to be VCS-neutral.
        worker = self.makeImportWorker()
        worker.run()

        bazaar_tree = worker.bazaar_branch_store.pull(
            self.source_details.branch_id, 'tmp-bazaar-tree')
        self.assertEqual(
            bazaar_tree.branch.last_revision(),
            worker.getBazaarWorkingTree().last_revision())

    def test_foreignTreeStored(self):
        # The worker archives the foreign tree after it has imported the new
        # revisions.
        # XXX: JonathanLange 2008-02-22: This test ought to be VCS-neutral.
        worker = self.makeImportWorker()
        worker.run()

        os.mkdir('tmp-foreign-tree')
        foreign_tree = worker.foreign_tree_store.fetchFromArchive(
            self.source_details, 'tmp-foreign-tree')
        self.assertDirectoryTreesEqual(
            foreign_tree.local_path, worker.getForeignTree().local_path)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
