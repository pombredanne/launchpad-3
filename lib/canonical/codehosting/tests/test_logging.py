# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the logging system of the sshserver."""

__metaclass__ = type

import codecs
import logging
from StringIO import StringIO
import unittest
import sys

from bzrlib.tests import TestCase as BzrTestCase

from canonical.codehosting.sshserver.server import set_up_logging
from canonical.testing import reset_logging


class TestLoggingSetup(BzrTestCase):

    def setUp(self):
        BzrTestCase.setUp(self)

        # Trap stderr.
        self._real_stderr = sys.stderr
        sys.stderr = codecs.getwriter('utf8')(StringIO())

        # We want to use Bazaar's default logging -- not its test logging --
        # so here we disable the testing logging system (which restores
        # default logging).
        self._finishLogFile()

    def tearDown(self):
        sys.stderr = self._real_stderr
        BzrTestCase.tearDown(self)
        # We don't use BaseLayer because we want to keep the amount of
        # pre-configured logging systems to an absolute minimum, in order to
        # make it easier to test this particular logging system.
        reset_logging()

    def test_returnsCodehostingLogger(self):
        # set_up_logging returns the 'codehosting' logger.
        self.assertIs(set_up_logging(), logging.getLogger('codehosting'))

    def test_codehostingLogDoesntGoToStderr(self):
        # Once set_up_logging is called, any messages logged to the
        # codehosting logger should *not* be logged to stderr. If they are,
        # they will appear on the user's terminal.

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
