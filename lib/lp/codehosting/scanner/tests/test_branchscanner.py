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

    def tearDown(self):
        errorlog.globalErrorUtility.raising = self._real_raising
        TestCaseWithFactory.tearDown(self)

    def assertLogged(self, logged_messages):
        """Assert that 'logged_messages' was logged by BranchScanner.

        :param logged_messages: A list of tuples of (level, message).
        """
        self.assertEqual(
            [(record.levelno, record.getMessage())
             for record in self._log_records],
            logged_messages)

    def raiseException(self, exception_factory, *args, **kwargs):
        """Construct an exception then raise it.

        Useful for making a function that raises a specific exception and can
        be passed to functional code.
        """
        raise exception_factory(*args, **kwargs)

    def raising(self, exc_info, request):
        """Used to replace the default globalErrorUtility.raising.

        We can't rely on the default implementation, since it uses the system
        clock to generate the OOPS ID.
        """
        request.oopsid = self._oopsid

    def scanWithError(self, branches, oopsid, exception_factory, *args, **kw):
        def scanOneBranch(branch):
            raise exception_factory(*args, **kw)
        self.scanner.scanOneBranch = scanOneBranch
        self._oopsid = oopsid
        self.scanner.scanBranches(branches)

    def test_log_unexpected_exception(self):
        # If scanOneBranch raises an unexpected exception, `logScanFailure`
        # will generate an OOPS, and log the error.
        error_message = self.factory.getUniqueString()
        branch = self.factory.makeAnyBranch()
        self.scanWithError([branch], 'OOPS', Exception, error_message)
        self.assertLogged(
            [(logging.INFO,
              ('OOPS: %s (%s)' % (error_message, branch.unique_name)))])

    def test_error_in_exception_str(self):
        # If getting the string of the exception raises an error, then
        # logScanFailure logs that exception and says that the error is
        # unknown.
        class BrokenException(Exception):
            def __str__(self):
                raise RuntimeError("Broken exception")
        branch = self.factory.makeAnyBranch()
        self.scanWithError([branch], 'OOPS', BrokenException)
        self.assertLogged([
            (40, 'ERROR WHILE GETTING EXCEPTION MESSAGE'),
            (20, ('OOPS: ERROR WHILE GETTING EXCEPTION MESSAGE (%s)'
                  % branch.unique_name))])

    def test_safe_str_normal(self):
        # _safe_str returns the str() of its argument.
        self.assertEqual('foo', self.scanner._safe_str('foo'))
        self.assertEqual('5', self.scanner._safe_str(5))

    def test_safe_str_returns_unknown_on_exception(self):
        # _safe_str returns the unknown parameter if str(obj) raises an
        # exception.
        class BrokenStr:
            def __str__(self):
                1/0
        broken = BrokenStr()
        self.assertEqual(
            'unknown', self.scanner._safe_str(broken, unknown='unknown'))

    def test_safe_str_logs_on_exception(self):
        # If _safe_str is called on an object for which str(obj) raises an
        # exception, then that exception is logged.
        class BrokenStr:
            def __str__(self):
                1/0
        broken = BrokenStr()
        self.scanner._safe_str(broken, unknown='unknown')
        self.assertLogged([(logging.ERROR, 'unknown')])

    def test_failsafe_normal(self):
        # _failsafe runs the callable given to it and returns its value.
        self.assertEqual(
            9, self.scanner._failsafe(None, None, lambda x: x * x, 3))

    def test_failsafe_reraises_keyboard_interrupt(self):
        # We never ever want to stop KeyboardInterrupt from being raised.
        self.assertRaises(
            KeyboardInterrupt,
            self.scanner._failsafe,
            None, None, self.raiseException, KeyboardInterrupt)

    def test_failsafe_reraises_system_exit(self):
        # We never ever want to stop SystemExit from being raised.
        self.assertRaises(
            SystemExit,
            self.scanner._failsafe,
            None, None, self.raiseException, SystemExit)

    def test_failsafe_returns_default_on_error(self):
        # _failsafe returns the given default value if the function raises.
        self.assertEqual(
            'default', self.scanner._failsafe(None, 'default', lambda: 1/0))

    def test_failsafe_logs_on_error(self):
        # _failsafe logs an error if the given callable raises an error.
        self.scanner._failsafe('log message', 'default', lambda: 1/0)
        self.assertLogged([(logging.ERROR, 'log message')])

    def test_logScanFailure_raises(self):
        # If logScanFailure raises for whatever reason, we log the error and
        # keep going.
        self.scanner.logScanFailure = lambda *args: 1/0
        self.scanWithError(
            [self.factory.makeAnyBranch()], 'OOPS', Exception, 'foo')
        self.assertLogged([(logging.ERROR, 'Error while trying to log: foo')])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
