# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests of the branch interface."""

__metaclass__ = type

from bzrlib.branch import BranchFormat as BzrBranchFormat
from bzrlib.bzrdir import BzrDirFormat
from bzrlib.repository import format_registry as repo_format_registry
from unittest import TestCase, TestLoader

from canonical.launchpad.interfaces import (
    BranchFormat, ControlFormat, RepositoryFormat)

class TestFormatSupport(TestCase):
    """Ensure the launchpad format list is up-to-date.

    While ideally we would ensure that the lists of markers were the same,
    early branch and repo formats did not use markers.  (The branch/repo
    was implied by the control dir format.)"""

    def test_control_format_complement(self):
        self.bzrlib_is_subset(BzrDirFormat._formats.keys(), ControlFormat)

    def test_branch_format_complement(self):
        self.bzrlib_is_subset(BzrBranchFormat._formats.keys(), BranchFormat)

    def test_repository_format_complement(self):
        self.bzrlib_is_subset(repo_format_registry.keys(), RepositoryFormat)

    def bzrlib_is_subset(self, bzrlib_formats, launchpad_enum):
        """Ensure the bzr format marker list is a subset of launchpad."""
        bzrlib_format_strings = set(bzrlib_formats)
        launchpad_format_strings = set(format.title for format
                                       in launchpad_enum.items)
        self.assertEqual(
            set(), bzrlib_format_strings.difference(launchpad_format_strings))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
