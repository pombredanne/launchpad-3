#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import sys
import os
import pty
import resource
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
        self.bzrworking = self.sandbox_helper.path('bzrworking')
        self.version = pybaz.Version('importd@example.com/test--branch--0')

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

    def bzrBranch(self):
        """Return the bzrlib Branch object for the produced branch."""
        return bzrlib.branch.Branch.open(self.bzrworking)

    def baz2bzrPath(self):
        """Filename of the baz2bzr script, used for spawning the script."""
        # Use the saved cwd to turn __file__ into an absolute path
        return os.path.join(self.sandbox_helper.here, baz2bzr.__file__)

    def callBaz2bzr(self, args):
        """Execute baz2bzr with the provided argument list.

        Does not redirect stdio so baz2bzr can be traced with pdb.

        :raise AssertionError: if the exit code is non-zero.
        """
        retcode = call([sys.executable, self.baz2bzrPath()] + args)
        assert retcode == 0, 'baz2bzr failed (status %d)' % retcode

    def pipeBaz2bzr(self, args):
        """Execute baz2bzr on pipes with the provided argument list.

        :return: stdout and stderr read from a single pipe
        :raise AssertionError: if the exit code is non-zero.
        """
        process = Popen([sys.executable, self.baz2bzrPath()] + args,
                        stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        output, error = process.communicate()
        unused = error
        retcode = process.returncode
        assert retcode == 0, 'baz2bzr failed (status %d)\s%s' % (retcode, output)
        return output

    def ptyBaz2bzr(self, args):
        """Execute baz2bzr in a pty with the provided argument list.

        :return: output read from the pty
        :raise AssertionError: if the exit code is non-zero
        """
        # That part was lifted from pexpect.py and simplified to remove
        # compatibility code.
        pid, child_fd = pty.fork()
        if pid == 0: # Child
            child_fd = sys.stdout.fileno()
            max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            for i in range (3, max_fd):
                try:
                    os.close (i)
                except OSError:
                    pass
            args = [sys.executable, self.baz2bzrPath()] + args
            try:
                os.execvp(sys.executable, args)
            finally:
                # If execvp fails, we do not want an exception to bubble up
                # into the callers
                os._exit(2)

        # Read all output. That will deadlock if the the child process tries to
        # read input. We cannot close input without closing output as well. If
        # deadlocking turns out to be a problem, we can raise non-blocking read
        # code from pexpect.py and kill the suprocess after a reasonable time
        # (5 minutes?).
        child_file = os.fdopen(child_fd)
        output = child_file.read()
        child_file.close()
        pid, sts = os.waitpid(pid, 0)

        # Exit status handling was lifted from subprocess.py
        if os.WIFSIGNALED(sts):
            returncode = -os.WTERMSIG(sts)
        elif os.WIFEXITED(sts):
            returncode = os.WEXITSTATUS(sts)
        else:
            # Should never happen
            raise RuntimeError("Unknown child exit status!")

        assert returncode == 0, (
            'baz2bzr failed (status %d)\n%s' % (returncode, output))
        return output
        

class TestBaz2bzrFeatures(Baz2bzrTestCase):

    def test_conversion(self):
        # test the initial import
        self.extractCannedArchive(1)
        self.registerCannedArchive()
        self.callBaz2bzr(
            ['-q', self.version.fullname, self.bzrworking, '/dev/null'])
        branch = self.bzrBranch()
        history = branch.revision_history()
        self.assertEqual(len(history), 2)
        self.assertRevisionMatchesExpected(branch, 0)
        self.assertRevisionMatchesExpected(branch, 1)
        # test updating the bzr branch
        self.extractCannedArchive(2)
        self.callBaz2bzr(
            ['-q', self.version.fullname, self.bzrworking, '/dev/null'])
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

    def test_pipe_output(self):
        self.extractCannedArchive(1)
        self.registerCannedArchive()
        output = self.pipeBaz2bzr(
            [self.version.fullname, self.bzrworking, '/dev/null'])
        self.assertEqual(output, '\n'.join(self.expected_lines))

    def test_pty_output(self):
        self.extractCannedArchive(1)
        self.registerCannedArchive()
        output = self.ptyBaz2bzr(
            [self.version.fullname, self.bzrworking, '/dev/null'])
        self.assertEqual(output, '\r\n'.join(self.expected_lines))

    expected_lines = [
        '0/2 revisions',
        '1/2 revisions',
        '2/2 revisions',
        'Cleaning up',
        'Import complete.',
        ''] # empty item denotes final newline


TestUtil.register(__name__)
