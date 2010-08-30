# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for MockLogger."""

__metaclass__ = type

from cStringIO import StringIO
import logging
import unittest

from lp.testing.logger import MockLogger


class TestMockLogger(unittest.TestCase):
    def setUp(self):
        self.logger = MockLogger(StringIO())

    def assertOutput(self, expected):
        self.logger.outfile.seek(0)
        self.assertEqual(self.logger.outfile.read(), expected)

    def test_log_literal(self):
        # If just a string is given, it is printed out literally.
        self.logger.log('foo')
        self.assertOutput('log> foo\n')

    def test_log_with_arguments(self):
        # If a format string and arguments are given, string
        # formatting is performed.
        self.logger.log('foo %s %d', 'bar', 1)
        self.assertOutput('log> foo bar 1\n')

    def test_log_format_string_without_arguments(self):
        # If a format string is given without arguments, string
        # formatting is not performed.
        self.logger.log('foo %s %d')
        self.assertOutput('log> foo %s %d\n')

    def test_log_with_format_string_in_exc_info(self):
        # If an exception occurs with '%s' in the backtrace, string
        # formatting is not attempted (so a crash is avoided).
        try:
            1/0 # %s
        except Exception:
            self.logger.log('foo', exc_info=True)

        self.logger.outfile.seek(0)
        output = self.logger.outfile.read()
        self.assertTrue(output.endswith(
            'ZeroDivisionError: integer division or modulo by zero\n'))
        self.assertTrue('1/0 # %s' in output)

    def test_setLevel(self):
        # setLevel should alter the value returned by getEffectiveLevel.
        self.assertEqual(self.logger.getEffectiveLevel(), logging.INFO)
        self.logger.setLevel(logging.ERROR)
        self.assertEqual(self.logger.getEffectiveLevel(), logging.ERROR)

    def test_info_works_with_default_level(self):
        # As the default level is INFO, info() should do something by
        # default.
        self.logger.info('foobar')
        self.assertOutput('log> foobar\n')

    def test_info_respects_log_level(self):
        # If we set the level to ERROR, info() should do nothing.
        self.logger.setLevel(logging.ERROR)
        self.logger.info('foobar')
        self.assertOutput('')


def test_suite():
        return unittest.TestLoader().loadTestsFromName(__name__)
