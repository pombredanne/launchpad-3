# Copyright 2007 Canonical Ltd.  All rights reserved.
"""cronscripts/buildd-* tests."""

__metaclass__ = type

import os
import subprocess
import sys
from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.testing import LaunchpadLayer

from contrib.glock import GlobalLock

class TestCronscriptBase(TestCase):
    """Buildd cronscripts test classes."""
    layer = LaunchpadLayer

    def setUp(self):
        self.layer.setUp()

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

    def runBuilddQueueBuilder(self, extra_args=[]):
        return self.runCronscript("buildd-queue-builder.py", extra_args)

    def runBuilddSlaveScanner(self, extra_args=[]):
        return self.runCronscript("buildd-slave-scanner.py", extra_args)

    def getBuilddMasterLock(self):
        """Returns a GlobalLock instance for build-master default lockfile."""
        from canonical.launchpad.scripts.base import LOCK_PATH
        from canonical.buildmaster.master import master_lockfilename
        lockfile_path = os.path.join(LOCK_PATH, master_lockfilename)
        return GlobalLock(lockfile_path)

    def assertRuns(self, runner, *args):
        """Invokes given runner with given arguments.

        Asserts the result code is 0 (zero) and returns a triple containing:
        (result_code, standart_output, error_output).
        """
        rc, out, err = runner()
        self.assertEqual(0, rc, "Err:\n%s" % err)
        return rc, out, err

    def assertLocked(self, runner, *args):
        """Acquire build-master lockfile and run the given runner.

        Asserts the output mentions only the lockfile conflict.
        Before return releases the locally acquired lockfile.
        """
        lock = self.getBuilddMasterLock(*args)
        lock.acquire()
        rc, out, err = self.assertRuns(runner, *args)
        self.assertEqual(
            ['INFO    creating lockfile',
             'INFO    Lockfile /var/lock/build-master in use'],
            err.splitlines(),
            "Not expected output:\n%s" % err)
        lock.release()

    def testRunSlaveScanner(self):
        """Check if buildd-slave-scanner runs without errors."""
        self.assertRuns(runner=self.runBuilddSlaveScanner)

    def testRunSlaveScannerLocked(self):
        """Check is buildd-slave-scanner.py respect build-master lock."""
        self.assertLocked(runner=self.runBuilddSlaveScanner)

    def testRunQueueBuilder(self):
        """Check if buildd-queue-builder runs without errors."""
        self.assertRuns(runner=self.runBuilddQueueBuilder)

    def testRunQueueBuilderLocked(self):
        """Check is buildd-queue-builder.py respect build-master lock."""
        self.assertLocked(runner=self.runBuilddQueueBuilder)

    def testRunQueueBuilderLockedByCronDaily(self):
        """Check if buildd-queue-builder respect cron.daily lock.

        Additionally to the 0 (zero) exit code we also want to ensure that
        no output is generated.
        """
        lock = open(config.builddmaster.crondaily_lockfile, 'w')
        lock.write('Go away !')
        lock.close()
        rc, out, err = self.assertRuns(runner=self.runBuilddQueueBuilder)
        self.assertEqual('', err.strip(), "Output should be empty:\n%s" % err)
        os.remove(config.builddmaster.crondaily_lockfile)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
