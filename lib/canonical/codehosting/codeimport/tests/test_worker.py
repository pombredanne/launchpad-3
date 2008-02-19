# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the code import worker."""

__metaclass__ = type

import os
import shutil
import tempfile
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.errors import NoSuchFile
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport import get_transport
from bzrlib.urlutils import join as urljoin

from canonical.cachedproperty import cachedproperty
from canonical.codehosting.codeimport.worker import (
    BazaarBranchStore, ForeignBranchStore, get_default_bazaar_branch_store,
    get_default_foreign_branch_store)
from canonical.codehosting.tests.helpers import (
    create_branch_with_one_revision)
from canonical.config import config
from canonical.launchpad.interfaces import BranchType, BranchTypeError
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing import LaunchpadScriptLayer


class WorkerTest(TestCaseWithTransport):
    """Base test case for things that test the code import worker.

    Provides Bazaar testing features, access to Launchpad objects and
    factories for some code import objects.
    """

    layer = LaunchpadScriptLayer

    @cachedproperty
    def factory(self):
        return LaunchpadObjectFactory()

    def makeCodeImport(self, svn_branch_url=None, cvs_root=None,
                       cvs_module=None):
        return self.factory.makeCodeImport(
            svn_branch_url=svn_branch_url, cvs_root=cvs_root,
            cvs_module=cvs_module)

    def makeTemporaryDirectory(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(directory))
        return directory


class TestBazaarBranchStore(WorkerTest):
    """Tests for `BazaarBranchStore`."""

    def setUp(self):
        super(TestBazaarBranchStore, self).setUp()
        code_import = self.factory.makeCodeImport()
        self.temp_dir = self.makeTemporaryDirectory()
        self.branch = code_import.branch

    def makeBranchStore(self):
        return BazaarBranchStore(self.get_transport())

    def test_defaultStore(self):
        # The default store is at config.codeimport.bazaar_branch_store.
        store = get_default_bazaar_branch_store()
        self.assertEqual(
            store.transport.base.rstrip('/'),
            config.codeimport.bazaar_branch_store.rstrip('/'))

    def test_getNewBranch(self):
        # If there's no Bazaar branch for the code import object, then pull
        # creates a new Bazaar working tree.
        store = self.makeBranchStore()
        bzr_working_tree = store.pull(self.branch, self.temp_dir)
        self.assertEqual([], bzr_working_tree.branch.revision_history())

    def test_pushBranchThenPull(self):
        # After we've pushed up a branch to the store, we can then pull it
        # from the store.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.branch, tree)
        new_tree = store.pull(self.branch, self.temp_dir)
        self.assertEqual(
            tree.branch.last_revision(), new_tree.branch.last_revision())

    def test_pushTwiceThenPull(self):
        # We can push up a branch to the store twice and then pull it from the
        # store.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.branch, tree)
        store.push(self.branch, tree)
        new_tree = store.pull(self.branch, self.temp_dir)
        self.assertEqual(
            tree.branch.last_revision(), new_tree.branch.last_revision())

    def test_pushNonImportBranch(self):
        # push() raises a BranchTypeError if you try to push a non-imported
        # branch.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        self.assertRaises(BranchTypeError, store.push, db_branch, tree)

    def test_pullNonImportBranch(self):
        # pull() raises a BranchTypeError if you try to pull a non-imported
        # branch.
        store = self.makeBranchStore()
        db_branch = self.factory.makeBranch(BranchType.HOSTED)
        self.assertRaises(BranchTypeError, store.pull, db_branch, 'tree')

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
        store.push(self.branch, tree)
        self.assertIsDirectory('doesntexist', self.get_transport())

    def test_storedLocation(self):
        # push() puts the branch in a directory named after the branch ID on
        # the BazaarBranchStore's transport.
        store = self.makeBranchStore()
        tree = create_branch_with_one_revision('original')
        store.push(self.branch, tree)
        new_tree = self.fetchBranch(
            urljoin(store.transport.base, '%08x' % self.branch.id),
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
            store._getMirrorURL(self.branch),
            sftp_prefix + '%08x' % self.branch.id)

    def test_sftpPrefixNoSlash(self):
        # If the prefix has no trailing slash, one should be added. It's very
        # easy to forget a trailing slash in the importd configuration.
        sftp_prefix_noslash = 'sftp://example/base'
        store = BazaarBranchStore(get_transport(sftp_prefix_noslash))
        self.assertEqual(
            store._getMirrorURL(self.branch),
            sftp_prefix_noslash + '/' + '%08x' % self.branch.id)


class MockForeignWorkingTree:
    """Working tree that records calls to checkout and update."""

    def __init__(self, local_path):
        self.local_path = local_path
        self.log = []

    def checkout(self):
        self.log.append('checkout')

    def update(self):
        self.log.append('update')


class TestForeignBranchStore(WorkerTest):

    def assertCheckedOut(self, tree):
        self.assertEqual(['checkout'], tree.log)

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

    def assertUpdated(self, tree):
        self.assertEqual(['update'], tree.log)

    def setUp(self):
        """Set up a code import job to import a SVN branch."""
        super(TestForeignBranchStore, self).setUp()
        self.code_import = self.makeCodeImport()
        self.temp_dir = self.makeTemporaryDirectory()
        self._log = []

    def makeForeignBranchStore(self, transport=None):
        """Make a foreign branch store.

        The store is in a different directory to the local working directory.
        """
        def _getForeignBranch(code_import, target_path):
            return MockForeignWorkingTree(target_path)
        if transport is None:
            transport = self.get_transport('remote')
        store = ForeignBranchStore(transport)
        store._getForeignBranch = _getForeignBranch
        return store

    def test_getForeignBranchSubversion(self):
        # _getForeignBranch() returns a Subversion working tree for Subversion
        # code imports.
        store = ForeignBranchStore(None)
        svn_import = self.makeCodeImport(
            svn_branch_url=self.factory.getUniqueURL())
        working_tree = store._getForeignBranch(svn_import, 'path')
        self.assertIsSameRealPath(working_tree.local_path, 'path')
        self.assertEqual(working_tree.remote_url, svn_import.svn_branch_url)

    def test_getForeignBranchCVS(self):
        # _getForeignBranch() returns a CVS working tree for CVS code imports.
        store = ForeignBranchStore(None)
        cvs_import = self.makeCodeImport(cvs_root='root', cvs_module='module')
        working_tree = store._getForeignBranch(cvs_import, 'path')
        self.assertIsSameRealPath(working_tree.local_path, 'path')
        self.assertEqual(working_tree.root, cvs_import.cvs_root)
        self.assertEqual(working_tree.module, cvs_import.cvs_module)

    def test_defaultStore(self):
        # The default store is at config.codeimport.foreign_branch_store.
        store = get_default_foreign_branch_store()
        self.assertEqual(
            store.transport.base.rstrip('/'),
            config.codeimport.foreign_branch_store.rstrip('/'))

    def test_getNewBranch(self):
        # If the branch store doesn't have an archive of the foreign branch,
        # then fetching the branch actually pulls in from the original site.
        store = self.makeForeignBranchStore()
        tree = store.fetchFromSource(self.code_import, self.temp_dir)
        self.assertCheckedOut(tree)

    def test_archiveBranch(self):
        # Once we have a checkout of a foreign branch, we can archive it so
        # that we can retrieve it more reliably in the future.
        store = self.makeForeignBranchStore()
        foreign_branch = store.fetchFromSource(
            self.code_import, self.temp_dir)
        store.archive(self.code_import, foreign_branch)
        self.assertTrue(
            store.transport.has('%08x.tar.gz' % self.code_import.branch.id),
            "Couldn't find '%08x.tar.gz'" % self.code_import.branch.id)

    def test_makeDirectories(self):
        # archive() tries to create the base directory of the branch store if
        # it doesn't already exist.
        store = self.makeForeignBranchStore(self.get_transport('doesntexist'))
        foreign_branch = store.fetchFromSource(
            self.code_import, self.temp_dir)
        store.archive(self.code_import, foreign_branch)
        self.assertIsDirectory('doesntexist', self.get_transport())

    def test_fetchFromArchiveFailure(self):
        # If a branch has not been archived yet, but we try to retrieve it
        # from the archive, then we get a NoSuchFile error.
        store = self.makeForeignBranchStore()
        self.assertRaises(
            NoSuchFile,
            store.fetchFromArchive, self.code_import, self.temp_dir)

    def test_fetchFromArchive(self):
        # After archiving a branch, we can retrieve it from the store -- the
        # tarball gets downloaded and extracted.
        store = self.makeForeignBranchStore()
        foreign_branch = store.fetchFromSource(
            self.code_import, self.temp_dir)
        store.archive(self.code_import, foreign_branch)
        new_temp_dir = self.makeTemporaryDirectory()
        foreign_branch2 = store.fetchFromArchive(
            self.code_import, new_temp_dir)
        self.assertEqual(new_temp_dir, foreign_branch2.local_path)
        self.assertDirectoryTreesEqual(self.temp_dir, new_temp_dir)

    def test_fetchFromArchiveUpdates(self):
        # The local working tree is updated with changes from the remote
        # branch after it has been fetched from the archive.
        store = self.makeForeignBranchStore()
        foreign_branch = store.fetchFromSource(
            self.code_import, self.temp_dir)
        store.archive(self.code_import, foreign_branch)
        new_temp_dir = self.makeTemporaryDirectory()
        foreign_branch2 = store.fetchFromArchive(
            self.code_import, new_temp_dir)
        self.assertUpdated(foreign_branch2)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
