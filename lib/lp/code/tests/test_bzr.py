# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.code.bzr."""

__metaclass__ = type

from bzrlib.tests import TestCaseInTempDir

from lp.code.bzr import (
    BranchFormat,
    branch_revision_history,
    ControlFormat,
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


class TestBranchRevisionHistory(TestCaseInTempDir):
    """Tests for lp.code.bzr.branch_revision_history."""

    def test_empty(self):
        branch = self.make_branch('test')
        self.assertEquals([], branch_revision_history(branch))

    def test_some_commits(self):
        wt = self.make_branch_and_tree('test')
        wt.commit('acommit', rev_id='A')
        wt.commit('bcommit', rev_id='B')
        wt.commit('ccommit', rev_id='C')
        self.assertEquals(['A', 'B', 'C'], branch_revision_history(wt.branch))
