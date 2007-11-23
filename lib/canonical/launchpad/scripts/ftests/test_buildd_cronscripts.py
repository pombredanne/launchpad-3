# Copyright 2007 Canonical Ltd.  All rights reserved.
"""cronscripts/buildd-* tests."""

__metaclass__ = type

import os
import subprocess
import sys
from unittest import TestCase, TestLoader

from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad.database.build import Build
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.interfaces import BuildStatus
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.buildd import RetryDepwait
from canonical.launchpad.scripts.base import LaunchpadScriptFailure
from canonical.testing import LaunchpadLayer


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

    def runBuilddQueueBuilder(self, extra_args=None):
        if extra_args is None:
            extra_args = []
        return self.runCronscript("buildd-queue-builder.py", extra_args)

    def runBuilddSlaveScanner(self, extra_args=None):
        if extra_args is None:
            extra_args = []
        return self.runCronscript("buildd-slave-scanner.py", extra_args)

    def runBuilddRetryDepwait(self, extra_args=None):
        if extra_args is None:
            extra_args = []
        return self.runCronscript("buildd-retry-depwait.py", extra_args)

    def assertRuns(self, runner, *args):
        """Invokes given runner with given arguments.

        Asserts the result code is 0 (zero) and returns a triple containing:
        (result_code, standart_output, error_output).
        """
        rc, out, err = runner()
        self.assertEqual(0, rc, "Err:\n%s" % err)
        return rc, out, err

    def testRunSlaveScanner(self):
        """Check if buildd-slave-scanner runs without errors."""
        self.assertRuns(runner=self.runBuilddSlaveScanner)

    def testRunQueueBuilder(self):
        """Check if buildd-queue-builder runs without errors."""
        self.assertRuns(runner=self.runBuilddQueueBuilder)

    def testRunRetryDepwait(self):
        """Check if buildd-retry-depwait runs without errors."""
        self.assertRuns(runner=self.runBuilddRetryDepwait)


class TestRetryDepwait(LaunchpadZopelessTestCase):
    """Test RetryDepwait buildd script class."""

    def setUp(self):
        """Store the number of pending builds present before run the tests."""
        self.number_of_pending_builds = self.getPendingBuilds().count()

    def getPendingBuilds(self):
        return Build.selectBy(buildstate=BuildStatus.NEEDSBUILD)

    def getRetryDepwait(self, distribution=None):
        test_args = ['-n']
        if distribution is not None:
            test_args.extend(['-d', distribution])

        retry_depwait = RetryDepwait(name='retry-depwait', test_args=test_args)
        # Swallowing all log messages.
        retry_depwait.logger = FakeLogger()
        def message(self, prefix, *stuff, **kw):
            pass
        retry_depwait.logger.message = message
        return retry_depwait

    def testUnknownDistribution(self):
        """A error is raised on unknown distributions."""
        retry_depwait = self.getRetryDepwait(distribution='foobar')
        self.assertRaises(LaunchpadScriptFailure, retry_depwait.main)

    def testEmptyRun(self):
        """Check the results of a run against pristine sampledata.

        Since the only record in MANUALDEPWAIT in sampledata can't be
        satisfied we expect the number of pending builds to be constant.
        """
        retry_depwait = self.getRetryDepwait()
        retry_depwait.main()
        self.assertEqual(
            self.number_of_pending_builds, self.getPendingBuilds().count())

    def testWorkingRun(self):
        """Modify sampledata and expects a new pending build to be created."""
        depwait_build = Build.get(12)
        depwait_build.dependencies = 'pmount'
        flush_database_updates()

        retry_depwait = self.getRetryDepwait()
        retry_depwait.main()
        self.layer.commit()

        self.assertEqual(
            self.number_of_pending_builds + 1, self.getPendingBuilds().count())
        self.assertEqual(depwait_build.buildstate.name, 'NEEDSBUILD')
        self.assertEqual(depwait_build.buildqueue_record.lastscore, 1005)

def test_suite():
    return TestLoader().loadTestsFromName(__name__)
