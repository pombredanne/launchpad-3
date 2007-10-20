# Copyright 2007 Canonical Ltd.  All rights reserved.
"""cronscripts/buildd-* tests."""

__metaclass__ = type

import os
import subprocess
import sys
from unittest import TestCase, TestLoader

from canonical.config import config
from canonical.buildmaster.master import (
    BuilddMaster, BUILDMASTER_ADVISORY_LOCK_KEY, BUILDMASTER_LOCKFILENAME)
from canonical.database.sqlbase import cursor
from canonical.database.postgresql import (
    acquire_advisory_lock, clear_all_advisory_locks)
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.scripts.base import LOCK_PATH
from canonical.testing import LaunchpadLayer

from contrib.glock import GlobalLock


class TestBuilddCronscriptBase(TestCase):

    def runCronscript(self, name, extra_args):
        """Run given cronscript, returning the result and output.

        Always set verbosity level.
        """
        script = os.path.join(config.root, "cronscripts", name)
        args = [sys.executable, script, "-v"]
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def runBuilddQueueBuilder(self, extra_args=None):
        if extra_args is None:
            extra_args = []
        return self.runCronscript("buildd-queue-builder.py", extra_args)

    def runBuilddSlaveScanner(self, extra_args=None):
        if extra_args is None:
            extra_args = []
        return self.runCronscript("buildd-slave-scanner.py", extra_args)

    def getBuilddMasterLock(self):
        """Returns a GlobalLock instance for build-master default lockfile."""
        lockfile_path = os.path.join(LOCK_PATH, BUILDMASTER_LOCKFILENAME)
        return GlobalLock(lockfile_path)

    def assertRuns(self, runner, **kw_args):
        """Invokes given runner with given arguments.

        Asserts the result code is 0 (zero) and returns a triple containing:
        (result_code, standart_output, error_output).
        """
        rc, out, err = runner(**kw_args)
        self.assertEqual(0, rc, "Err:\n%s" % err)
        return rc, out, err

    def assertLocked(self, runner, **kw_args):
        """Acquire build-master lockfile and run the given runner.

        Asserts the output mentions only the lockfile conflict.
        Before return releases the locally acquired lockfile.
        """
        lock = self.getBuilddMasterLock(**kw_args)
        lock.acquire()
        rc, out, err = self.assertRuns(runner,  **kw_args)
        self.assertEqual(
            ['INFO    creating lockfile',
             'INFO    Lockfile /var/lock/build-master in use'],
            err.strip().splitlines(),
            "Not expected output:\n%s" % err)
        lock.release()


class TestBuilddCronscripts(TestBuilddCronscriptBase):
    """Buildd cronscripts test classes."""
    layer = LaunchpadLayer

    def setUp(self):
        self.layer.setUp()

    def testRunSlaveScanner(self):
        """Check if buildd-slave-scanner runs without errors."""
        self.assertRuns(runner=self.runBuilddSlaveScanner)

    def testRunSlaveScannerLocked(self):
        """Check if buildd-slave-scanner.py respects build-master lock."""
        self.assertLocked(runner=self.runBuilddSlaveScanner)

    def testRunQueueBuilder(self):
        """Check if buildd-queue-builder runs without errors."""
        self.assertRuns(runner=self.runBuilddQueueBuilder)

    def testDryRunQueueBuilder(self):
        """Check if buildd-queue-builder runs in 'dry-run' mode."""
        self.assertRuns(runner=self.runBuilddQueueBuilder, extra_args=['-n'])

    def testRunQueueBuilderLocked(self):
        """Check if buildd-queue-builder.py respects build-master lock."""
        self.assertLocked(runner=self.runBuilddQueueBuilder)


class TestBuilddCronscriptsAdvisoryLock(
    TestBuilddCronscriptBase, LaunchpadZopelessTestCase):

    def setUp(self):
        """Setup a database cursor."""
        self.local_cursor = cursor()

    def tearDown(self):
        """Ensure all advisory locks aquired in during tests are released."""
        clear_all_advisory_locks(self.local_cursor)

    def acquireBuilddmasterAdvisoryLock(self):
        """Acquire builddmaster postgres advisory lock."""
        lock_acquired = acquire_advisory_lock(
            self.local_cursor, BUILDMASTER_ADVISORY_LOCK_KEY)
        self.assertTrue(lock_acquired)

    def testAdvisoryLockForQueueBuilder(self):
        """buildd-queue-builder respects buildmaster advisory lock."""
        self.acquireBuilddmasterAdvisoryLock()
        rc, out, err = self.runBuilddQueueBuilder()
        self.assertEqual(rc, 1)
        self.assertTrue('script is already running' in err)

    def testAdvisoryLockForSlaveScanner(self):
        """buildd-slave-scanner respects buildmaster advisory lock."""
        self.acquireBuilddmasterAdvisoryLock()
        rc, out, err = self.runBuilddSlaveScanner()
        self.assertEqual(rc, 1)
        self.assertTrue('script is already running' in err)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
