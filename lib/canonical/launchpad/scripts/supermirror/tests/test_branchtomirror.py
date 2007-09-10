# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Unit tests for branchtomirror.py."""

__metaclass__ = type

import unittest

from canonical.launchpad.scripts.supermirror import branchtomirror
from canonical.launchpad.database import Branch
from canonical.launchpad.webapp import canonical_url
from canonical.testing import LaunchpadZopelessLayer


# Define a bunch of different fake format classes to pass to identical_formats

class BzrDirFormatA:
    pass

class BzrDirFormatB:
    pass

class BranchFormatA:
    pass

class BranchFormatB:
    pass

class RepoFormatA:
    pass

class RepoFormatB:
    pass


class StubObjectWithFormat:
    """A stub object with a _format attribute, like bzrdir and repositories."""
    def __init__(self, format):
        self._format = format


class StubBranch:
    """A stub branch object that just has formats."""
    def __init__(self, bzrdir_format, repo_format, branch_format):
        self.bzrdir = StubObjectWithFormat(bzrdir_format)
        self.repository = StubObjectWithFormat(repo_format)
        self._format = branch_format


class IdenticalFormatsTestCase(unittest.TestCase):
    """Test case for identical_formats function."""

    def testAllIdentical(self):
        # identical_formats should return True when both branches have the same
        # bzrdir, repository, and branch formats.
        self.failUnless(
            branchtomirror.identical_formats(
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA()),
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA())))

    def testDifferentBzrDirFormats(self):
        # identical_formats should return False when both branches have the
        # different bzrdir formats.
        self.failIf(
            branchtomirror.identical_formats(
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA()),
                StubBranch(BzrDirFormatB(), RepoFormatA(), BranchFormatA())))

    def testDifferentRepositoryFormats(self):
        # identical_formats should return False when both branches have the
        # different repository formats.
        self.failIf(
            branchtomirror.identical_formats(
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA()),
                StubBranch(BzrDirFormatA(), RepoFormatB(), BranchFormatA())))

    def testDifferentBranchFormats(self):
        # identical_formats should return False when both branches have the
        # different branch formats.
        self.failIf(
            branchtomirror.identical_formats(
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA()),
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatB())))


class TestBranchKind(unittest.TestCase):
    """Test cases for methods used to classify branches."""

    def iterSampleBranches(self):
        sample_urls = [
            'http://escudero.ubuntu.com:680/0000000e', # import branch
            'http://example.com/gnome-terminal/main', # mirror branch
            '/tmp/sftp-test/branches/00/00/00/19', # upload branch
            ]
        for source in sample_urls:
            yield branchtomirror.BranchToMirror(
                src=source, dest=None,
                branch_status_client=None, branch_id=None,
                branch_unique_name=None)

    def testIsUploadBranch(self):
        # isUploadBranch is true if and only if the source url is that of an
        # upload branch.
        is_upload_values = [branch_to_mirror.isUploadBranch()
            for branch_to_mirror in self.iterSampleBranches()]
        self.assertEqual(is_upload_values, [False, False, True])

    def testIsMirrorBranch(self):
        # isMirrorBranch is true if and only if the source url is that of a
        # mirror branch.
        is_mirror_values = [branch_to_mirror.isMirrorBranch()
            for branch_to_mirror in self.iterSampleBranches()]
        self.assertEqual(is_mirror_values, [False, True, False])

    def testIsImportBranch(self):
        # isImportBranch is true if and only if the source url is that of an
        # import branch.
        is_import_values = [branch_to_mirror.isImportBranch()
            for branch_to_mirror in self.iterSampleBranches()]
        self.assertEqual(is_import_values, [True, False, False])


class TestCanonicalUrl(unittest.TestCase):
    """Test cases for rendering the canonical url of a branch."""

    layer = LaunchpadZopelessLayer

    def testCanonicalUrlConsistent(self):
        # BranchToMirror._canonical_url is consistent with
        # webapp.canonical_url, if the provided unique_name is correct.
        branch = Branch.get(15)
        # Check that the unique_name used in this test is consistent with the
        # sample data. This is an invariant of the test, so use a plain assert.
        unique_name = 'name12/gnome-terminal/main'
        assert branch.unique_name == '~' + unique_name
        branch_to_mirror = branchtomirror.BranchToMirror(
            src=None, dest=None, branch_status_client=None,
            branch_id=None, branch_unique_name=unique_name)
        # Now check that our implementation of canonical_url is consistent with
        # the canonical one.
        self.assertEqual(
            branch_to_mirror._canonical_url(), canonical_url(branch))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

