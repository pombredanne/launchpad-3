# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the script run on the remote server."""

__metaclass__ = type

from StringIO import StringIO
import sys
import unittest

from testtools import TestCase

from devscripts.ec2test.remote import SummaryResult


class TestSummaryResult(TestCase):
    """Tests for `SummaryResult`."""

    def makeException(self, factory=None, *args, **kwargs):
        if factory is None:
            factory = RuntimeError
        try:
            raise factory(*args, **kwargs)
        except:
            return sys.exc_info()

    def test_formatError(self):
        # SummaryResult._formatError() combines the name of the test, the kind
        # of error and the details of the error in a nicely-formatted way.
        result = SummaryResult(None)
        output = result._formatError('FOO', 'test', 'error')
        expected = '%s\nFOO: test\n%s\nerror\n' % (
            result.double_line, result.single_line)
        self.assertEqual(expected, output)

    def test_addError_writes_at_end_of_run(self):
        # SummaryResult.addError() prints a nicely-formatted error.
        #
        # First, use printError to build the error text we expect.
        test = self
        stream = StringIO()
        result = SummaryResult(stream)
        error = self.makeException()
        result.printError(
            'ERROR', test, result._exc_info_to_string(error, test))
        expected = stream.getvalue()
        # Now, call addError and check that it matches.
        stream = StringIO()
        result = SummaryResult(stream)
        result.addError(test, error)
        self.assertEqual('', stream.getvalue())
        result.stopTestRun()
        self.assertEqual(expected, stream.getvalue())

    def test_addFailure_writes_at_end_of_run(self):
        # SummaryResult.addFailure() prints a nicely-formatted error.
        #
        # First, use printError to build the error text we expect.
        test = self
        stream = StringIO()
        result = SummaryResult(stream)
        error = self.makeException(test.failureException)
        result.printError(
            'FAILURE', test, result._exc_info_to_string(error, test))
        expected = stream.getvalue()
        # Now, call addFailure and check that it matches.
        stream = StringIO()
        result = SummaryResult(stream)
        result.addFailure(test, error)
        self.assertEqual('', stream.getvalue())
        result.stopTestRun()
        self.assertEqual(expected, stream.getvalue())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
