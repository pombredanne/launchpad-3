# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.code.bzr."""

__metaclass__ = type

from lp.code.bzr import (
    BranchFormat, ControlFormat, get_branch_formats, RepositoryFormat)
from bzrlib.tests import TestCaseInTempDir


class TestGetBranchFormats(TestCaseInTempDir):

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
