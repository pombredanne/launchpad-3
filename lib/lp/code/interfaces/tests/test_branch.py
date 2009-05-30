# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests of the branch interface."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from bzrlib.branch import BranchFormat as BzrBranchFormat
from bzrlib.bzrdir import BzrDirFormat
from bzrlib.repository import format_registry as repo_format_registry

from lp.code.interfaces.branch import (
    BranchFormat, BRANCH_FORMAT_UPGRADE_PATH, ControlFormat, RepositoryFormat,
    REPOSITORY_FORMAT_UPGRADE_PATH)


class TestFormatSupport(TestCase):
    """Ensure the launchpad format list is up-to-date.

    While ideally we would ensure that the lists of markers were the same,
    early branch and repo formats did not use markers.  (The branch/repo
    was implied by the control dir format.)
    """

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

    def test_repositoryDescriptions(self):
        self.checkDescriptions(RepositoryFormat)

    def test_branchDescriptions(self):
        self.checkDescriptions(BranchFormat)

    def test_controlDescriptions(self):
        self.checkDescriptions(ControlFormat)

    def checkDescriptions(self, format_enums):
        for item in format_enums.items:
            description = item.description
            if description.endswith('\n'):
                description = description[:-1]
            self.assertTrue(len(description.split('\n')) == 1,
                            item.description)


class TestBranchFormatUpgradePath(TestCase):
    """Tests for BRANCH_FORMAT_UPGRADE_PATH."""

    def test_branch_format_enum_as_keys(self):
        # Each element of the BranchFormat enum should have a corresponding key
        # in the BRANCH_FORMAT_UPGRADE_PATH dict.
        for format in BranchFormat.items:
            self.assertTrue(BRANCH_FORMAT_UPGRADE_PATH.has_key(format))


class TestRepositoryFormatUpgradePath(TestCase):
    """Tests for BRANCH_FORMAT_UPGRADE_PATH."""

    def test_repository_format_enum_as_keys(self):
        # Each element of the BranchFormat enum should have a corresponding key
        # in the BRANCH_FORMAT_UPGRADE_PATH dict.
        for format in RepositoryFormat.items:
            self.assertTrue(REPOSITORY_FORMAT_UPGRADE_PATH.has_key(format))

    def test_repository_format_upgrades_dont_cross_streams(self):
        # Repository formats should not try to upgrade a format that doesn't
        # support rich roots or subtrees to a format that does, and vice versa.
        for format in REPOSITORY_FORMAT_UPGRADE_PATH.keys():
            upgrade_format = REPOSITORY_FORMAT_UPGRADE_PATH[format]
            if upgrade_format is None:
                continue
            try:
                format_start = repo_format_registry.get(format.title)
            except KeyError: # We used a fake format string.
                continue
            format_end = repo_format_registry.get(
                upgrade_format().get_format_string())
            self.assertEqual(
                getattr(format_start, 'rich_root_data', False),
                getattr(format_end, 'rich_root_data', False))
            self.assertEqual(
                getattr(format_start, 'supports_tree_reference', False),
                getattr(format_end, 'supports_tree_reference', False))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
