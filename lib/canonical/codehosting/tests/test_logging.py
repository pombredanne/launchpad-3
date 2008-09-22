# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the logging system of the sshserver."""

__metaclass__ = type

import codecs
import logging
import os
import shutil
from StringIO import StringIO
import tempfile
import unittest
import sys

from bzrlib.tests import TestCase as BzrTestCase

from canonical.config import config
from canonical.codehosting.sshserver import set_up_logging
from canonical.testing import reset_logging


class TestLoggingSetup(BzrTestCase):

    def setUp(self):
        BzrTestCase.setUp(self)

        # Configure the debug logfile
        self._real_debug_logfile = config.codehosting.debug_logfile
        file_handle, filename = tempfile.mkstemp()
        config.codehosting.debug_logfile = filename

        # Trap stderr.
        self._real_stderr = sys.stderr
        sys.stderr = codecs.getwriter('utf8')(StringIO())

        # We want to use Bazaar's default logging -- not its test logging --
        # so here we disable the testing logging system (which restores
        # default logging).
        self._finishLogFile()

    def tearDown(self):
        sys.stderr = self._real_stderr
        config.codehosting.debug_logfile = self._real_debug_logfile
        BzrTestCase.tearDown(self)
        # We don't use BaseLayer because we want to keep the amount of
        # pre-configured logging systems to an absolute minimum, in order to
        # make it easier to test this particular logging system.
        reset_logging()

    def test_loggingSetUpAssertionFailsIfParentDirectoryIsNotADirectory(self):
        # set_up_logging fails with an AssertionError if it cannot create the
        # directory that the log file will go in.
        file_handle, filename = tempfile.mkstemp()
        def remove_file():
            os.unlink(filename)
        self.addCleanup(remove_file)

        config.codehosting.debug_logfile = os.path.join(filename, 'debug.log')
        self.assertRaises(AssertionError, set_up_logging)

    def test_makesLogDirectory(self):
        # If the specified logfile is in a directory that doesn't exist, then
        # set_up_logging makes that directory.
        directory = tempfile.mkdtemp()
        def remove_directory():
            shutil.rmtree(directory)
        self.addCleanup(remove_directory)

        config.codehosting.debug_logfile = os.path.join(
            directory, 'subdir', 'debug.log')
        set_up_logging()
        self.failUnless(os.path.isdir(os.path.join(directory, 'subdir')))

    def test_returnsCodehostingLogger(self):
        # set_up_logging returns the 'codehosting' logger.
        self.assertIs(set_up_logging(), logging.getLogger('codehosting'))

    def test_codehostingLogGoesToDebugLogfile(self):
        # Once set_up_logging is called, messages logged to the codehosting
        # logger are stored in config.codehosting.debug_logfile.

        set_up_logging()

        # Make sure that a logged message goes to the debug logfile
        logging.getLogger('codehosting').debug('Hello hello')
        self.failUnless(
            open(config.codehosting.debug_logfile).read().endswith(
                'Hello hello\n'))

    def test_codehostingLogDoesntGoToStderr(self):
        # Once set_up_logging is called, any messages logged to the
        # codehosting logger should *not* be logged to stderr. If they are,
        # they will appear on the user's terminal.

        set_up_logging()

        # Make sure that a logged message does not go to stderr.
        logging.getLogger('codehosting').info('Hello hello')
        self.assertEqual(sys.stderr.getvalue(), '')

    def test_codehostingLogDoesntGoToStderrEvenWhenNoLogfile(self):
        # Once set_up_logging is called, any messages logged to the
        # codehosting logger should *not* be logged to stderr, even if there's
        # no debug_logfile set.

        config.codehosting.debug_logfile = None
        set_up_logging()

        # Make sure that a logged message does not go to stderr.
        logging.getLogger('codehosting').info('Hello hello')
        self.assertEqual(sys.stderr.getvalue(), '')

    def test_leavesBzrHandlersUnchanged(self):
        # Bazaar's log handling is untouched by set_up_logging.
        root_handlers = logging.getLogger('').handlers
        bzr_handlers = logging.getLogger('bzr').handlers

        set_up_logging()

        self.assertEqual(root_handlers, logging.getLogger('').handlers)
        self.assertEqual(bzr_handlers, logging.getLogger('bzr').handlers)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
