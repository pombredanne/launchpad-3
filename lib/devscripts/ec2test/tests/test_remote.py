# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the script run on the remote server."""

__metaclass__ = type

from StringIO import StringIO
import unittest

from devscripts.ec2test.remote import SummaryResult


class TestSummaryResult(unittest.TestCase):
    """Tests for `SummaryResult`."""

    def test_printError(self):
        # SummaryResult.printError() prints out the name of the test, the kind
        # of error and the details of the error in a nicely-formatted way.
        stream = StringIO()
        result = SummaryResult(stream)
        result.printError('FOO', 'test', 'error')
        expected = '%sFOO: test\n%serror\n' % (
            result.double_line, result.single_line)
        self.assertEqual(expected, stream.getvalue())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
