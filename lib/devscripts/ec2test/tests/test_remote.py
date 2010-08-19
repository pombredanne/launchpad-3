# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the script run on the remote server."""

__metaclass__ = type

from StringIO import StringIO
import sys
import unittest

from devscripts.ec2test.remote import SummaryResult


class TestSummaryResult(unittest.TestCase):
    """Tests for `SummaryResult`."""

    def makeException(self, factory=None, *args, **kwargs):
        if factory is None:
            factory = RuntimeError
        try:
            raise factory(*args, **kwargs)
        except:
            return sys.exc_info()

    def test_printError(self):
        # SummaryResult.printError() prints out the name of the test, the kind
        # of error and the details of the error in a nicely-formatted way.
        stream = StringIO()
        result = SummaryResult(stream)
        result.printError('FOO', 'test', 'error')
        expected = '%sFOO: test\n%serror\n' % (
            result.double_line, result.single_line)
        self.assertEqual(expected, stream.getvalue())

    def test_addError(self):
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
        self.assertEqual(expected, stream.getvalue())

    def test_addFailure(self):
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
        self.assertEqual(expected, stream.getvalue())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
