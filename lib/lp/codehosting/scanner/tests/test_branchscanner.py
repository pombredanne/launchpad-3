# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the branch scanner script."""

__metaclass__ = type

import logging
import unittest

from canonical.launchpad.webapp import errorlog
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.codehosting.scanner.branch_scanner import BranchScanner
from lp.testing import TestCaseWithFactory


class AppendingHandler(logging.Handler):
    """Log handler that appends everything logged to a list."""

    def __init__(self, record_list):
        logging.Handler.__init__(self)
        self._record_list = record_list

    def emit(self, record):
        self._record_list.append(record)


class TestErrorHandling(TestCaseWithFactory):
    """Test the error handling in the BranchScanner class.

    We scan a whole bunch of branches in the same process. If any of them
    raise unexpected errors, we need to handle and report these errors without
    affecting the scanning of the next branch.

    In particular, this means we need to guard against errors being raised in
    our error handling code.
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        log = logging.Logger(self.factory.getUniqueString())
        self._log_records = []
        log.addHandler(AppendingHandler(self._log_records))
        self.scanner = BranchScanner(None, log)
        # Used as an OOPS id in log messages. Assign to this variable to
        # change the OOPS ID used.
        self._oopsid = None
        self._real_raising = errorlog.globalErrorUtility.raising
        errorlog.globalErrorUtility.raising = self.raising

    def assertLogged(self, logged_messages):
        """Assert that 'logged_messages' was logged by BranchScanner.

        :param logged_messages: A list of tuples of (level, message).
        """
        self.assertEqual(
            [(record.levelno, record.getMessage())
             for record in self._log_records],
            logged_messages)

    def raising(self, exc_info, request):
        """Used to replace the default globalErrorUtility.raising.

        We can't rely on the default implementation, since it uses the system
        clock to generate the OOPS ID.
        """
        request.oopsid = self._oopsid

    def test_log_unexpected_exception(self):
        # If scanOneBranch raises an unexpected exception, `logScanFailure`
        # will generate an OOPS, and log the error.
        self.scanner.scanOneBranch = lambda branch: 1/0
        self._oopsid = 'OOPS'
        self.scanner.scanBranches([self.factory.makeAnyBranch()])
        self.assertLogged(
            [(logging.INFO,
              ('OOPS: integer division or modulo by zero '
               '(~person-name10/product-name5/branch12)'))])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
