#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import sys
import os
import shutil
from subprocess import Popen, call, STDOUT, PIPE
import unittest

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
        """Extract the canned archive with the given sequence number.

        Remove any previously extracted canned archive.
        """
        basedir = os.path.dirname(__file__)
        # Use the saved cwd to turn __file__ into an absolute path
        basedir = os.path.join(self.sandbox_helper.here, basedir)
        tarball = os.path.join(basedir, 'importd@example.com-%d.tgz' % number)
        target_dir = self.sandbox_helper.path('archives')
        archive_path = os.path.join(target_dir, 'importd@example.com')
        if os.path.isdir(archive_path):
            shutil.rmtree(archive_path)
        retcode = call(['tar', 'xzf', tarball], cwd=target_dir)
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
        return bzrlib.branch.Branch.open(self.bzrBranchPath())

    def callBaz2bzr(self, args):
        """Execute baz2bzr with the provided argument list.

        Does not redirect stdio so baz2bzr can be traced with pdb.

        :raise AssertionError: if the exit code is non-zero.
        """
        # Use the saved cwd to turn __file__ into an absolute path
        script = os.path.join(self.sandbox_helper.here, baz2bzr.__file__)
        retcode = call([sys.executable, script] + args)
        assert retcode == 0, 'baz2bzr failed (status %d)' % retcode


class TestBaz2bzrFeatures(Baz2bzrTestCase):

    def test_conversion(self):
        # test the initial import
        self.extractCannedArchive(1)
        self.registerCannedArchive()
        bzrworking = self.sandbox_helper.path('bzrworking')
        version = self.cannedArchiveVersion()
        self.callBaz2bzr([version.fullname, bzrworking, '/dev/null'])
        branch = self.bzrBranch()
        history = branch.revision_history()
        self.assertEqual(len(history), 2)
        self.assertRevisionMatchesExpected(branch, 0)
        self.assertRevisionMatchesExpected(branch, 1)
        # test updating the bzr branch
        self.extractCannedArchive(2)
        self.callBaz2bzr([version.fullname, bzrworking, '/dev/null'])
        history = branch.revision_history()
        self.assertEqual(len(history), 3)
        self.assertRevisionMatchesExpected(branch, 0)
        self.assertRevisionMatchesExpected(branch, 1)
        self.assertRevisionMatchesExpected(branch, 2)


    def assertRevisionMatchesExpected(self, branch, index):
        """Match revision attributes against expected data."""
        history = branch.revision_history()
        expected_revs = [
            ('Arch-1:importd@example.com%test--branch--0--base-0',
             1140542478.0, None, 'david', 'Initial revision\n',
             {'converted-by': 'launchpad.net', 'cscvs-id': 'MAIN.1'}),
            ('Arch-1:importd@example.com%test--branch--0--patch-1',
             1140542480.0, None, 'david', 'change 1\n',
             {'converted-by': 'launchpad.net', 'cscvs-id': 'MAIN.2'}),
            ('Arch-1:importd@example.com%test--branch--0--patch-2',
             1140542509.0, None, 'david', 'change 2\n',
             {'converted-by': 'launchpad.net', 'cscvs-id': 'MAIN.3'})]
        revision = branch.get_revision(history[index])
        revision_attrs = (
            revision.revision_id,
            revision.timestamp,
            revision.timezone,
            revision.committer,
            revision.message,
            revision.properties)
        self.assertEqual(revision_attrs, expected_revs[index])


TestUtil.register(__name__)
