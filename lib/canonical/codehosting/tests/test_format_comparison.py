# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Tests for utilities in worker.py"""

__metaclass__ = type

import unittest

from canonical.codehosting.puller import worker


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
            worker.identical_formats(
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA()),
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA())))

    def testDifferentBzrDirFormats(self):
        # identical_formats should return False when both branches have the
        # different bzrdir formats.
        self.failIf(
            worker.identical_formats(
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA()),
                StubBranch(BzrDirFormatB(), RepoFormatA(), BranchFormatA())))

    def testDifferentRepositoryFormats(self):
        # identical_formats should return False when both branches have the
        # different repository formats.
        self.failIf(
            worker.identical_formats(
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA()),
                StubBranch(BzrDirFormatA(), RepoFormatB(), BranchFormatA())))

    def testDifferentBranchFormats(self):
        # identical_formats should return False when both branches have the
        # different branch formats.
        self.failIf(
            worker.identical_formats(
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatA()),
                StubBranch(BzrDirFormatA(), RepoFormatA(), BranchFormatB())))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

