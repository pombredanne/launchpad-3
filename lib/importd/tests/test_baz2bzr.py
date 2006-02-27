#!/usr/bin/env python
# Copyright (c) 2006 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import sys
import os
import pty
import resource
import shutil
from StringIO import StringIO
from subprocess import Popen, call, STDOUT, PIPE
import unittest

import pybaz
import bzrlib.branch

import transaction
from canonical.launchpad.database import ProductSet

from importd import baz2bzr
from importd.tests import TestUtil
from importd.tests.helpers import SandboxHelper, ZopelessHelper

class ProductSeriesHelper(object):
    """Helper for tests that use the testing ProductSeries."""

    def setUp(self):
        self.zopeless_helper = ZopelessHelper()
        self.zopeless_helper.setUp()
        self.version = pybaz.Version('importd@example.com/test--branch--0')
        self.setUpTestSeries()

    def tearDown(self):
        self.zopeless_helper.tearDown()
        self.series_id = None
        self.series = None

    def setUpTestSeries(self):
        product = ProductSet()['gnome-terminal']
        series = product.newSeries('importd-test', displayname='', summary='')
        self.series = series
        self.series_id = series.id
        parser = pybaz.NameParser(self.version.fullname)
        series.targetarcharchive = self.version.archive.name
        series.targetarchcategory = self.version.category.nonarch
        series.targetarchbranch = parser.get_branch()
        series.targetarchversion = parser.get_version()
        transaction.commit()


class Baz2bzrTestCase(unittest.TestCase):
    """Base class for baz2bzr test cases."""

    def setUp(self):
        self.sandbox_helper = SandboxHelper()
        self.sandbox_helper.setUp()
        self.series_helper = ProductSeriesHelper()
        self.series_helper.setUp()
        self.version = self.series_helper.version
        self.series_id = self.series_helper.series_id
        self.sandbox_helper.mkdir('archives')
        self.bzrworking = self.sandbox_helper.path('bzrworking')

    def tearDown(self):
        self.sandbox_helper.tearDown()
        self.series_helper.tearDown()
        self.series_id = None

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

    def baz2bzrEnv(self):
        """Build the baz2bzr environment dictionnary."""
        environ = dict(os.environ)
        environ['LP_DBNAME'] = 'launchpad_ftest'
        environ['LP_DBUSER'] = 'importd'
        return environ

    def callBaz2bzr(self, args):
        """Execute baz2bzr with the provided argument list.

        Does not redirect stdio so baz2bzr can be traced with pdb.

        :raise AssertionError: if the exit code is non-zero.
        """
        retcode = call(
            [sys.executable, self.baz2bzrPath()] + args, env=self.baz2bzrEnv())
        assert retcode == 0, 'baz2bzr failed (status %d)' % retcode

    def pipeBaz2bzr(self, args, status=0):
        """Execute baz2bzr on pipes with the provided argument list.

        :return: stderr and stdout combined in a single string.
        :raise AssertionError: if the exit code is non-zero.
        """
        process = Popen(
            [sys.executable, self.baz2bzrPath()] + args,
            stdin=PIPE, stdout=PIPE, stderr=STDOUT, env=self.baz2bzrEnv())
        output, error = process.communicate()
        unused = error
        retcode = process.returncode
        assert retcode == status, (
            'baz2bzr failed (status %d)\n%s' % (retcode, output))
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
            new_env = self.baz2bzrEnv()
            for key in os.environ.keys():
                del os.environ[key]
            for key, value in new_env.items():
                os.environ[key] = value
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
        self.callBaz2bzr(['-q', str(self.series_id), '/dev/null'])
        branch = self.bzrBranch()
        history = branch.revision_history()
        self.assertEqual(len(history), 2)
        self.assertRevisionMatchesExpected(branch, 0)
        self.assertRevisionMatchesExpected(branch, 1)
        # test updating the bzr branch
        self.extractCannedArchive(2)
        self.callBaz2bzr(['-q', str(self.series_id), '/dev/null'])
        history = branch.revision_history()
        self.assertEqual(len(history), 3)
        self.assertRevisionMatchesExpected(branch, 0)
        self.assertRevisionMatchesExpected(branch, 1)
        self.assertRevisionMatchesExpected(branch, 2)

    # Here we make sure that the baz-import functionality is indeed used
    # and that we are using the version which has been modified to parse
    # the cscvs metadata and add launchpad.net advertising. Since we are
    # always importing from the same baz archive (generated by cscvs), we
    # must always get the same revision properties.
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

    def assertRevisionMatchesExpected(self, branch, index):
        """Match revision attributes against expected data."""
        history = branch.revision_history()
        revision = branch.get_revision(history[index])
        revision_attrs = (
            revision.revision_id,
            revision.timestamp,
            revision.timezone,
            revision.committer,
            revision.message,
            revision.properties)
        self.assertEqual(revision_attrs, self.expected_revs[index])

    def test_pipe_output(self):
        self.extractCannedArchive(1)
        self.registerCannedArchive()
        output = self.pipeBaz2bzr([str(self.series_id), '/dev/null'])
        self.assertEqual(output, '\n'.join(self.expected_lines))

    def test_pty_output(self):
        self.extractCannedArchive(1)
        self.registerCannedArchive()
        output = self.ptyBaz2bzr([str(self.series_id), '/dev/null'])
        self.assertEqual(output, '\r\n'.join(self.expected_lines))

    # expected_lines should be a reasonable amount of progress output. Enough
    # for the process no to spin for 20 minutes without producing output (and
    # be killed by buildbot). Not too much to avoid hitting the string
    # concatenation bug in buildbot. One line per revision is good.
    expected_lines = [
        '0/2 revisions',
        '1/2 revisions',
        '2/2 revisions',
        'Cleaning up',
        'Import complete.',
        ''] # empty item denotes final newline

    def test_blacklist(self):
        self.extractCannedArchive(1)
        self.registerCannedArchive()
        blacklist_path = self.sandbox_helper.path('blacklist')
        blacklist_file = open(blacklist_path, 'w')
        print >> blacklist_file, self.version.fullname
        blacklist_file.close()
        output = self.pipeBaz2bzr(
            [str(self.series_id), blacklist_path])
        expected = "blacklisted: %s\nNot exporting to bzr\n" % (
            self.version.fullname)
        self.assertEqual(output, expected)
        self.failIf(os.path.exists(self.bzrworking))


class TestBlacklistParser(unittest.TestCase):

    def assertBlacklistParses(self, blacklist, expected):
        stringio = StringIO(blacklist)
        result = baz2bzr.parseBlacklist(stringio)
        self.assertEqual(list(result), expected)

    def test_one(self):
        self.assertBlacklistParses('foo\n', ['foo'])
        self.assertBlacklistParses('foo', ['foo'])
        self.assertBlacklistParses('\nfoo', ['foo'])
        self.assertBlacklistParses(' foo \n', ['foo'])

    def test_empty(self):
        self.assertBlacklistParses('', [])
        self.assertBlacklistParses('\n', [])
        self.assertBlacklistParses(' \n', [])

    def test_two(self):
        self.assertBlacklistParses('foo\nbar\n', ['foo', 'bar'])
        self.assertBlacklistParses('foo\nbar', ['foo', 'bar'])
        self.assertBlacklistParses('foo\n\nbar\n', ['foo', 'bar'])


class TestProductSeries(unittest.TestCase):

    def setUp(self):
        self.series_helper = ProductSeriesHelper()
        self.series_helper.setUp()
        self.series = self.series_helper.series
        self.version = self.series_helper.version

    def tearDown(self):
        self.series_helper.tearDown()
        self.series = None

    def testArchFromSeries(self):
        arch_version = baz2bzr.archFromSeries(self.series)        
        self.assertEqual(arch_version, self.version.fullname)


TestUtil.register(__name__)
