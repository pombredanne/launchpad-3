# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.code.bzr."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from bzrlib.errors import NoSuchRevision
from bzrlib.revision import NULL_REVISION
from bzrlib.tests import (
    TestCaseInTempDir,
    TestCaseWithTransport,
    )

from lp.code.bzr import (
    branch_revision_history,
    BranchFormat,
    ControlFormat,
    get_ancestry,
    get_branch_formats,
    RepositoryFormat,
    )
from lp.testing import TestCase


class TestBazaarFormatEnum(TestCase):
    """Tests for the bazaar formats."""

    def test_branch_format_unrecognized(self):
        # Unknown branch formats are unrecognized.
        format = BranchFormat.get_enum('no-idea')
        self.assertEqual(BranchFormat.UNRECOGNIZED, format)

    def test_control_format_unrecognized(self):
        # Unknown control formats are unrecognized.
        format = ControlFormat.get_enum('no-idea')
        self.assertEqual(ControlFormat.UNRECOGNIZED, format)

    def test_repository_format_unrecognized(self):
        # Unknown repository formats are unrecognized.
        format = RepositoryFormat.get_enum('no-idea')
        self.assertEqual(RepositoryFormat.UNRECOGNIZED, format)


class TestGetBranchFormats(TestCaseInTempDir):
    """Tests for lp.code.bzr.get_branch_formats."""

    def test_get_branch_format_2a(self):
        # Test the 2a branch format.
        branch = self.make_branch('test', '2a')
        formats = get_branch_formats(branch)
        self.assertEqual(ControlFormat.BZR_METADIR_1, formats[0])
        self.assertEqual(BranchFormat.BZR_BRANCH_7, formats[1])
        self.assertEqual(RepositoryFormat.BZR_CHK_2A, formats[2])

    def test_get_branch_format_1_9(self):
        # Test the 1.9 branch format.
        branch = self.make_branch('test', '1.9')
        formats = get_branch_formats(branch)
        self.assertEqual(ControlFormat.BZR_METADIR_1, formats[0])
        self.assertEqual(BranchFormat.BZR_BRANCH_7, formats[1])
        self.assertEqual(RepositoryFormat.BZR_KNITPACK_6, formats[2])

    def test_get_branch_format_packs(self):
        # Test the packs branch format.
        branch = self.make_branch('test', 'pack-0.92')
        formats = get_branch_formats(branch)
        self.assertEqual(ControlFormat.BZR_METADIR_1, formats[0])
        self.assertEqual(BranchFormat.BZR_BRANCH_6, formats[1])
        self.assertEqual(RepositoryFormat.BZR_KNITPACK_1, formats[2])

    def test_get_branch_format_knits(self):
        # Test the knits branch format.
        branch = self.make_branch('test', 'knit')
        formats = get_branch_formats(branch)
        self.assertEqual(ControlFormat.BZR_METADIR_1, formats[0])
        self.assertEqual(BranchFormat.BZR_BRANCH_5, formats[1])
        self.assertEqual(RepositoryFormat.BZR_KNIT_1, formats[2])


class TestBranchRevisionHistory(TestCaseWithTransport):
    """Tests for lp.code.bzr.branch_revision_history."""

    def test_empty(self):
        branch = self.make_branch('test')
        self.assertEqual([], branch_revision_history(branch))

    def test_some_commits(self):
        branch = self.make_branch('test')
        tree = branch.bzrdir.create_workingtree()
        tree.commit('acommit', rev_id=b'A')
        tree.commit('bcommit', rev_id=b'B')
        tree.commit('ccommit', rev_id=b'C')
        self.assertEqual(
            [b'A', b'B', b'C'], branch_revision_history(tree.branch))


class TestGetAncestry(TestCaseWithTransport):
    """Tests for lp.code.bzr.get_ancestry."""

    def test_missing_revision(self):
        # If the revision does not exist, NoSuchRevision should be raised.
        branch = self.make_branch('test')
        self.assertRaises(
            NoSuchRevision, get_ancestry, branch.repository, b'orphan')

    def test_some(self):
        # Verify ancestors are included.
        branch = self.make_branch('test')
        tree = branch.bzrdir.create_workingtree()
        tree.commit('msg a', rev_id=b'A')
        tree.commit('msg b', rev_id=b'B')
        tree.commit('msg c', rev_id=b'C')
        self.assertEqual(
            set([b'A']), get_ancestry(branch.repository, b'A'))
        self.assertEqual(
            set([b'A', b'B']), get_ancestry(branch.repository, b'B'))
        self.assertEqual(
            set([b'A', b'B', b'C']), get_ancestry(branch.repository, b'C'))

    def test_children(self):
        # Verify non-mainline children are included.
        branch = self.make_branch('test')
        tree = branch.bzrdir.create_workingtree()
        tree.commit('msg a', rev_id=b'A')
        branch.generate_revision_history(NULL_REVISION)
        tree.set_parent_ids([])
        tree.commit('msg b', rev_id=b'B')
        branch.generate_revision_history(b'A')
        tree.set_parent_ids([b'A', b'B'])
        tree.commit('msg c', rev_id=b'C')
        self.assertEqual(
            set([b'A']), get_ancestry(branch.repository, b'A'))
        self.assertEqual(
            set([b'B']), get_ancestry(branch.repository, b'B'))
        self.assertEqual(
            set([b'A', b'B', b'C']), get_ancestry(branch.repository, b'C'))
