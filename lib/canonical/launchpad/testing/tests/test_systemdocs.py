# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for canonical.launchpad.testing.systemdocs module."""

__metaclass__ = type

import logging
import os
import shutil
import tempfile
import unittest

from zope.testing import doctest

from canonical.config import config
from canonical.launchpad.testing.systemdocs import (
    default_optionflags, LayeredDocFileSuite)


class LayeredDocFileSuiteTests(unittest.TestCase):
    """Tests for LayeredDocFileSuite()."""

    def setUp(self):
        self._orig_root = config.root
        # we need an empty story to test with, and it has to be in the
        # testing namespace
        self.tempdir = tempfile.mkdtemp(dir=os.path.dirname(__file__))

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        config.root = self._orig_root

    def makeTestFile(self, filename, content=''):
        test_filename = os.path.join(self.tempdir, filename)
        test_file = open(test_filename, 'w')
        test_file.write(content)
        test_file.close()

    def test_creates_test_suites(self):
        """Test that LayeredDocFileSuite creates test suites."""
        self.makeTestFile('foo.txt')
        self.makeTestFile('bar.txt')
        base = os.path.basename(self.tempdir)
        suite = LayeredDocFileSuite(
            os.path.join(base, 'foo.txt'),
            os.path.join(base, 'bar.txt'))
        self.assertTrue(isinstance(suite, unittest.TestSuite))

        [foo_test, bar_test] = list(suite)
        self.assertTrue(isinstance(foo_test, unittest.TestCase))
        self.assertEqual(os.path.basename(foo_test.id()), 'foo_txt')
        self.assertTrue(isinstance(bar_test, unittest.TestCase))
        self.assertEqual(os.path.basename(bar_test.id()), 'bar_txt')

    def test_set_layer(self):
        """Test that a layer can be applied to the created tests."""
        self.makeTestFile('foo.txt')
        base = os.path.basename(self.tempdir)
        # By default, no layer is applied to the suite.
        suite = LayeredDocFileSuite(os.path.join(base, 'foo.txt'))
        self.assertFalse(hasattr(suite, 'layer'))
        # But if one is passed as a keyword argument, it is applied:
        suite = LayeredDocFileSuite(
            os.path.join(base, 'foo.txt'), layer='some layer')
        self.assertEqual(suite.layer, 'some layer')

    def test_accepts_logging_arguments(self):
        """Test that stdout_logging argument is accepted."""
        self.makeTestFile('foo.txt')
        base = os.path.basename(self.tempdir)
        # Create a suite with logging turned on.
        suite = LayeredDocFileSuite(
            os.path.join(base, 'foo.txt'),
            stdout_logging=True, stdout_logging_level=logging.CRITICAL)
        # And one with it turned off.
        suite = LayeredDocFileSuite(
            os.path.join(base, 'foo.txt'), stdout_logging=False)

    def test_optionflags(self):
        """Test that a default set of option flags are applied."""
        self.makeTestFile('foo.txt')
        base = os.path.basename(self.tempdir)
        suite = LayeredDocFileSuite(os.path.join(base, 'foo.txt'))
        [foo_test] = list(suite)
        self.assertEqual(foo_test._dt_optionflags, default_optionflags)
        # If the optionflags argument is passed, it takes precedence:
        suite = LayeredDocFileSuite(
            os.path.join(base, 'foo.txt'), optionflags=doctest.ELLIPSIS)
        [foo_test] = list(suite)
        self.assertEqual(foo_test._dt_optionflags, doctest.ELLIPSIS)

    def test_strips_prefix(self):
        """Test that the Launchpad tree root is stripped from test names."""
        self.makeTestFile('foo.txt')
        base = os.path.basename(self.tempdir)
        # Set the Launchpad tree root to our temporary directory and
        # create a test suite.
        config.root = self.tempdir
        suite = LayeredDocFileSuite(os.path.join(base, 'foo.txt'))
        [foo_test] = list(suite)
        # The test ID and string representation have the prefix
        # stripped off.
        self.assertEqual(foo_test.id(), 'foo_txt')
        self.assertEqual(str(foo_test), 'foo.txt')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
