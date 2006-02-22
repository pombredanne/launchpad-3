#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import sys
import os
import unittest
from subprocess import Popen, call, STDOUT, PIPE

import pybaz
import bzrlib.branch

from importd import baz2bzr
from importd.tests import TestUtil
from importd.tests.helpers import SandboxHelper

class Baz2bzrTestCase(unittest.TestCase):
    """Base class for baz2bzr test cases."""

    def setUp(self):
        self.sandbox_helper = SandboxHelper()
        self.sandbox_helper.setUp()
        self.sandbox_helper.mkdir('archives')

    def tearDown(self):
        self.sandbox_helper.tearDown()

    def extractCannedArchive(self, number):
        """Extract the canned archive with the given sequence number."""
        basedir = os.dirname(__file__)
        tarball = os.path.join(basedir, 'importd@example.com-%d.tgz' % number)
        target_dir = self.sandbox_helper.path('archives')
        retcode = call(['tar', 'xzf', tarball], chdir=target_dir)
        assert retcode == 0, 'failed to extract canned archive %d' % number

    def registerCannedArchive(self):
        """Register a canned archive created by extractCannedArchive."""
        path = os.path.join(self.sandbox_helper.path('archives'),
                            'importd@example.com')
        location = pybaz.ArchiveLocation(path)
        location.register()

    def cannedArchiveVersion(self):
        """Return the pybaz.Version stored in the canned archives."""
        return pybaz.Version('importd@example.com/test--branch--0')

    def bzrBranchPath(self):
        """Return the path to the produced bzr branch."""
        return self.sandbox_helper.path('bzrworking')

    def bzrBranch(self):
        """Return the bzrlib Branch object for the produced branch."""
        return bzrlib.branch.Branch(self.bzrBranchPath())

    def pipeBaz2bzr(self, args):
        """Execute baz2bzr on pipes with the provided argument list.

        Return the combined output of its stdout and stderr output, and raise
        AssertionError if the exit code is non-zero.
        """
        script = os.dirname(baz2bzr.__file__)
        process = Popen(
            [sys.executable, script] + args,
            stdin=PIPE, stderr=STDOUT, stdout=PIPE)
        process.stdin.close()
        output = process.read()
        retcode = process.wait()
        assert retcode == 0, 'baz2bzr failed\n%s\nexit %d' % (output, retcode)
        return output


class TestBaz2bzrFeatures(Baz2bzrTestCase):

    def test_conversion(self):
        self.extractCannedArchive(1)
        self.registerCannedArchive()
        bzrworking = self.sandbox_helper('bzrworking')
        version = self.cannedArchiveVersion()
        self.pipeBaz2bzr([version.fullname, bzrworking, '/dev/null'])
        branch = self.bzrBranch()
        history = branch.revision_history()
        self.assertEqual(len(history), 2)
        rev0 = branch.get_revisions(history[0])
        expected_rev0 = (
            'revid', 'timestamp', 'timezone', 'committer', 'message', 'revprops')
        self.assertRevisionMatches(rev0, expected_rev0)
        rev1 = branch.get_revisions(history[1])
        expected_rev1 = (
            'revid', 'timestamp', 'timezone', 'committer', 'message', 'revprops')
        self.assertRevisionMatches(rev1, expected_rev1)

    def assertRevisionMatches(self, revision, expected):
        """Match revision attributes against expected data."""
        revision_attrs = (
            revision.revision_id,
            revision.timestamp,
            revision.timezone,
            revision.committer,
            revision.message,
            revision.properties)
        self.assertEqual(revision_attrs, expected)


TestUtil.register(__name__)
