# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import subprocess
import sys
import shutil
import tempfile
import unittest

from cStringIO import StringIO

from canonical.config import config
from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
from canonical.testing import LaunchpadZopelessLayer


class TestProcessUpload(unittest.TestCase):
    """Test the process-upload.py script."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.queue_location = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.queue_location)

    def runProcessUpload(self, extra_args=None, queue_location=None):
        """Run process-upload.py, returning the result and output."""
        if extra_args is None:
            extra_args = []
        if queue_location is None:
            queue_location = self.queue_location
        script = os.path.join(config.root, "scripts", "process-upload.py")
        args = [sys.executable, script, "-vvv", queue_location]
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def assertQueuePath(self, path):
        """Check if given path exists within the current queue_location."""
        probe_path = os.path.join(self.queue_location, path)
        self.assertTrue(
            os.path.exists(probe_path), "'%s' does not exist." % path)

    def testSimpleRun(self):
        """Try a simple process-upload run.

        Observe it creating the required directory tree for a given
        empty queue_location.
        """
        returncode, out, err = self.runProcessUpload()
        self.assertEqual(0, returncode)

        # directory tree in place.
        for directory in ['incoming', 'accepted', 'rejected', 'failed']:
            self.assertQueuePath(directory)

        # just to check if local assertion is working as expect.
        self.assertRaises(AssertionError, self.assertQueuePath, 'foobar')

    def testTopLevelLockFile(self):
        """Try a simple process-upload run.

        Expect it to exit earlier due the occupied lockfile
        """
        # acquire the process-upload lockfile locally
        from contrib.glock import GlobalLock
        locker = GlobalLock('/var/lock/process-upload-insecure.lock')
        locker.acquire()

        returncode, out, err = self.runProcessUpload(
            extra_args=['-C', 'insecure']
            )

        # the process-upload call terminated with ERROR and
        # proper log message
        self.assertEqual(1, returncode)
        self.assertEqual(
            ['INFO    creating lockfile',
             'DEBUG   Lockfile /var/lock/process-upload-insecure.lock in use'
             ], err.splitlines())

        # release the locally acquired lockfile
        locker.release()

    def testOopsCreation(self):
        """Try a simple process-upload run.

        Observe it creating the OOPS upon being passed a bogus queue
        location path.
        """
        returncode, out, err = self.runProcessUpload(
            queue_location='/bogus_path')
        self.assertEqual(0, returncode)

        error_utility = ErrorReportingUtility()
        error_report = error_utility.getLastOopsReport()
        fp = StringIO()
        error_report.write(fp)
        error_text = fp.getvalue()
        self.failUnless(
            error_text.find('Exception-Type: LaunchpadScriptFailure') >= 0,
            'Expected Exception type not found in OOPS report:\n%s'
            % error_text)

        expected_explanation = (
            'error-explanation=Exception while processing upload '
            '/bogus_path')
        self.failUnless(
            error_text.find(expected_explanation) >= 0,
            'Expected Exception text not found in OOPS report:\n%s'
            % error_text)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
