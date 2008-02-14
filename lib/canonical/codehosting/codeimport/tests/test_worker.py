# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the code import worker."""

__metaclass__ = type

import shutil
import tempfile
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.tests import TestCaseWithTransport
from bzrlib.transport import get_transport
from bzrlib.urlutils import join as urljoin

from canonical.cachedproperty import cachedproperty
from canonical.codehosting.codeimport.worker import (
    BazaarBranchStore, get_default_bazaar_branch_store)
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

    def makeTemporaryDirectory(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(directory))
        return directory


class TestBazaarBranchStore(WorkerTest):
    """Tests for `BazaarBranchStore`."""

    def setUp(self):
        WorkerTest.setUp(self)
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
