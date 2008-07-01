# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the integration between Twisted's logging and Launchpad's."""

__metaclass__ = type

import datetime
import logging
import pytz
import re
import shutil
import StringIO
import tempfile
from textwrap import dedent
from unittest import TestLoader

from twisted.python import log
from twisted.trial.unittest import TestCase

from canonical.config import config
from canonical.launchpad.webapp.errorlog import globalErrorUtility
from canonical.testing.layers import TwistedLayer
from canonical.twistedsupport.loggingsupport import OOPSLoggingObserver
from canonical.twistedsupport.tests.test_processmonitor import (
    makeFailure, suppress_stderr)


UTC = pytz.utc


class LoggingSupportTests(TestCase):

    layer = TwistedLayer

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.temp_dir)
        config.push('testing', dedent("""
            [error_reports]
            oops_prefix: O
            error_dir: %s
            copy_to_zlog: False
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
        self.flushLoggedErrors(RuntimeError)
        oops = globalErrorUtility.getOopsReport(error_time)
        self.assertEqual(oops.type, 'RuntimeError')
        self.assertLogMatches('^Logged OOPS id.*')

def test_suite():
    return TestLoader().loadTestsFromName(__name__)

