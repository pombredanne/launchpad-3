# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for `DirectBranchCommit`."""

__metaclass__ = type

from unittest import TestLoader

from bzrlib.branch import Branch as BzrBranch

from lp.code.model.directbranchcommit import (
    ConcurrentUpdateError, DirectBranchCommit)
from lp.testing import TestCaseWithFactory
from canonical.testing.layers import LaunchpadZopelessLayer


class TestDirectBranchCommit(TestCaseWithFactory):
    """Test `DirectBranchCommit`."""

    layer = LaunchpadZopelessLayer

    db_branch = None
    committer = None

    def setUp(self):
        super(TestDirectBranchCommit, self).setUp()
        self.useBzrBranches()

        self.series = self.factory.makeProductSeries()
        self.db_branch, tree = self.create_branch_and_tree(
            db_branch=self.db_branch, hosted=True)

        self.series.translations_branch = self.db_branch

        self._setUpCommitter()

    def _setUpCommitter(self, update_last_scanned_id=True):
        if self.committer:
            self.committer.unlock()

        self.committer = DirectBranchCommit(self.db_branch)
        if update_last_scanned_id:
            self.db_branch.last_scanned_id = (
                self.committer.bzrbranch.last_revision())

    def tearDown(self):
        self.committer.unlock()

    def _getContents(self):
        """Return branch contents as dict mapping filenames to contents."""
        contents = {}
        branch = BzrBranch.open(self.committer.db_branch.getPullURL())
        tree = branch.basis_tree()
        tree.lock_read()
        try:
            for dir, entries in tree.walkdirs():
                dirname, id = dir
                for entry in entries:
                    file_path, file_name, file_type = entry[:3]
                    if file_type == 'file':
                        stored_file = tree.get_file_by_path(file_path)
                        contents[file_path] = stored_file.read()
        finally:
            tree.unlock()

        return contents

    def test_DirectBranchCommit_commits_no_changes(self):
        # Committing to an empty branch leaves the branch empty.
        self.committer.commit('')
        self.assertEqual({}, self._getContents())

    def test_DirectBranchCommit_rejects_change_after_commit(self):
        # Changes are not accepted after commit.
        self.committer.commit('')
        self.assertRaises(AssertionError, self.committer.writeFile, 'x', 'y')

    def test_DirectBranchCommit_adds_file(self):
        # DirectBranchCommit can add a new file to the branch.
        self.committer.writeFile('file.txt', 'contents')
        self.committer.commit('')
        self.assertEqual({'file.txt': 'contents'}, self._getContents())

    def test_DirectBranchCommit_updates_file(self):
        # DirectBranchCommit can replace a file in the branch.
        self.committer.writeFile('file.txt', 'contents')
        self.committer.commit('')
        self._setUpCommitter()
        self.committer.writeFile('file.txt', 'changed')
        self.committer.commit('')
        self.assertEqual({'file.txt': 'changed'}, self._getContents())

    def test_DirectBranchCommit_creates_directories(self):
        # Files can be in subdirectories.
        self.committer.writeFile('a/b/c.txt', 'ctext')
        self.committer.commit('')
        self.assertEqual({'a/b/c.txt': 'ctext'}, self._getContents())

    def test_DirectBranchCommit_writes_new_file_twice(self):
        # If you write the same new file multiple times before
        # committing, the original wins.
        self.committer.writeFile('x.txt', 'aaa')
        self.committer.writeFile('x.txt', 'bbb')
        self.committer.commit('')
        self.assertEqual({'x.txt': 'aaa'}, self._getContents())

    def test_DirectBranchCommit_updates_file_twice(self):
        # If you update the same file multiple times before committing,
        # the original wins.
        self.committer.writeFile('y.txt', 'aaa')
        self.committer.commit('')
        self._setUpCommitter()
        self.committer.writeFile('y.txt', 'bbb')
        self.committer.writeFile('y.txt', 'ccc')
        self.committer.commit('')
        self.assertEqual({'y.txt': 'bbb'}, self._getContents())

    def test_DirectBranchCommit_detects_race_condition(self):
        # If the branch has been updated since it was last scanned,
        # attempting to commit to it will raise ConcurrentUpdateError.
        self.committer.writeFile('hi.c', 'main(){puts("hi world");}')
        self.committer.commit('')
        self._setUpCommitter(False)
        self.committer.writeFile('hi.py', 'print "hi world"')
        self.assertRaises(ConcurrentUpdateError, self.committer.commit, '')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
