# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the integration between Twisted's logging and Launchpad's."""

__metaclass__ = type

import datetime
import logging
import os
import re
import shutil
import StringIO
import tempfile
from textwrap import dedent

import pytz

from testtools.deferredruntest import (
    AsynchronousDeferredRunTest,
    flush_logged_errors,
    )

from twisted.python import log

from canonical.config import config
from canonical.launchpad.webapp.errorlog import globalErrorUtility
from lp.services.twistedsupport.loggingsupport import (
    LaunchpadLogFile,
    OOPSLoggingObserver,
    )
from lp.services.twistedsupport.tests.test_processmonitor import (
    makeFailure,
    suppress_stderr,
    )
from lp.testing import TestCase


UTC = pytz.utc


class LoggingSupportTests(TestCase):

    run_tests_with = AsynchronousDeferredRunTest

    def setUp(self):
        super(LoggingSupportTests, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        config.push('testing', dedent("""
            [error_reports]
            oops_prefix: O
            error_dir: %s
            """ % self.temp_dir))
        globalErrorUtility.configure()
        self.log_stream = StringIO.StringIO()
        self.logger = logging.getLogger('test')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler(self.log_stream))
        self.observer = OOPSLoggingObserver('test')

    def tearDown(self):
        config.pop('testing')
        globalErrorUtility.configure()
        super(LoggingSupportTests, self).tearDown()

    def assertLogMatches(self, pattern):
        """Assert that the messages logged by self.logger matches a regexp."""
        log_text = self.log_stream.getvalue()
        self.failUnless(re.match(pattern, log_text, re.M))

    @suppress_stderr
    def test_oops_reporting(self):
        # Calling log.err should result in an OOPS being logged.
        log.addObserver(self.observer.emit)
        self.addCleanup(log.removeObserver, self.observer.emit)
        error_time = datetime.datetime.now(UTC)
        fail = makeFailure(RuntimeError)
        log.err(fail, error_time=error_time)
        flush_logged_errors(RuntimeError)
        oops = self.oopses[-1]
        self.assertEqual(oops['type'], 'RuntimeError')
        self.assertLogMatches('^Logged OOPS id.*')


class TestLaunchpadLogFile(TestCase):

    def setUp(self):
        super(TestLaunchpadLogFile, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)

    def testInitialization(self):
        """`LaunchpadLogFile` initialization.

        It has proper default values for 'maxRotatedFiles' (5) and
        'compressLast' (3), although allows call sites to specify their own
        values.

        The initialization fails if the given 'compressLast' value is
        incoherent with 'maxRotatedFiles', like requesting the compression
        of more files that we have rotated.
        """
        # Default behavior.
        log_file = LaunchpadLogFile('test.log', self.temp_dir)
        self.assertEqual(5, log_file.maxRotatedFiles)
        self.assertEqual(3, log_file.compressLast)

        # Keeping only compressed rotated logs.
        log_file = LaunchpadLogFile(
            'test.log', self.temp_dir, maxRotatedFiles=1, compressLast=1)
        self.assertEqual(1, log_file.maxRotatedFiles)
        self.assertEqual(1, log_file.compressLast)

        # Inconsistent parameters, compression more than kept rotated files.
        self.assertRaises(
            AssertionError, LaunchpadLogFile, 'test.log', self.temp_dir,
            maxRotatedFiles=1, compressLast=2)

    def createTestFile(self, name, content='nothing'):
        """Create a new file in the test directory."""
        file_path = os.path.join(self.temp_dir, name)
        fd = open(file_path, 'w')
        fd.write(content)
        fd.close()
        return file_path

    def listTestFiles(self):
        """Return a ordered list of files in the test directory."""
        return sorted(os.listdir(self.temp_dir))

    def testListLogs(self):
        """Check `LaunchpadLogFile.listLogs`

        This lookup method return the rotated logfiles present in the
        logging directory. It ignores the current log file and extraneous.

        Only corresponding log files (plain and compressed) are returned,
        the newest first.
        """
        log_file = LaunchpadLogFile('test.log', self.temp_dir)
        self.assertEqual(['test.log'], self.listTestFiles())
        self.assertEqual([], log_file.listLogs())

        self.createTestFile('boing')
        self.assertEqual([], log_file.listLogs())

        self.createTestFile('test.log.2000-12-31')
        self.createTestFile('test.log.2000-12-30.bz2')
        self.assertEqual(
            ['test.log.2000-12-31', 'test.log.2000-12-30.bz2'],
            [os.path.basename(log_path) for log_path in log_file.listLogs()])

    def testRotate(self):
        """Check `LaunchpadLogFile.rotate`.

        Check if the log file is rotated as expected and only the specified
        number to rotated files are kept, also that the specified number of
        compressed files are created.
        """
        log_file = LaunchpadLogFile(
            'test.log', self.temp_dir, maxRotatedFiles=2, compressLast=1)

        # Monkey-patch DailyLogFile.suffix to be time independent.
        self.local_index = 0
        def testSuffix(tupledate):
            self.local_index += 1
            return str(self.local_index)
        log_file.suffix = testSuffix

        log_file.rotate()
        self.assertEqual(
            ['test.log', 'test.log.1'],
            self.listTestFiles())

        log_file.rotate()
        self.assertEqual(
            ['test.log', 'test.log.1.bz2', 'test.log.2'],
            self.listTestFiles())

        log_file.rotate()
        self.assertEqual(
            ['test.log', 'test.log.2.bz2', 'test.log.3'],
            self.listTestFiles())

