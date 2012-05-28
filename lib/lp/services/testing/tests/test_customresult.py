# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Parallel test glue."""

__metaclass__ = type

import string
import tempfile

from testtools import (
    TestCase,
    )

from lp.services.testing.customresult import (
    filter_tests,
    )
from lp.testing.layers import BaseLayer

import unittest


NEWLINE = '\n'


class FakeTestCase(unittest.TestCase):
    """A minimal TestCase that can be instantiated."""
    def __init__(self, name, *args, **kwargs):
        super(FakeTestCase, self).__init__(*args, **kwargs)
        self.name = name
    def id(self):
        return self.name
    def runTest(self):
        pass
    def __str__(self):
        return self.id()
    def __repr__(self):
        return str(self)


class TestFilterTests(TestCase):

    layer = BaseLayer

    def setUp(self):
        super(TestFilterTests, self).setUp()

    def writeFile(self, fd, contents):
        for line in contents:
            fd.write(line + NEWLINE)
        fd.flush()

    def test_ordering(self):
        # Tests should be returned in the order seen in the testfile.
        layername = 'layer-1'
        testnames = ['d', 'c', 'a']
        suite = unittest.suite.TestSuite()
        for letter in string.lowercase:
            suite.addTest(FakeTestCase(letter))
        with tempfile.NamedTemporaryFile() as fd:
            self.writeFile(fd, testnames)
            do_filter = filter_tests(fd.name)
            results = do_filter({layername: suite})
        self.assertEqual(1, len(results))
        self.assertTrue(layername in results)
        suite = results[layername]
        self.assertEqual(testnames, [t.id() for t in suite])

    def test_layer_separation(self):
        # Tests must be kept in their layer.
        suite1 = unittest.suite.TestSuite()
        suite2 = unittest.suite.TestSuite()
        # Create one layer with the 'a'..'m'.
        for letter in string.lowercase[:13]:
            suite1.addTest(FakeTestCase(letter))
        # And another layer with 'n'..'z'.
        for letter in string.lowercase[13:]:
            suite2.addTest(FakeTestCase(letter))
        testnames = ['a', 'b', 'c', 'z', 'y', 'x']
        with tempfile.NamedTemporaryFile() as fd:
            self.writeFile(fd, testnames)
            do_filter = filter_tests(fd.name)
            results = do_filter({'layer1': suite1,
                                 'layer2': suite2})
        self.assertEqual(2, len(results))
        self.assertEqual(['layer1', 'layer2'], sorted(results.keys()))
        self.assertEqual(['a', 'b', 'c'], [t.id() for t in results['layer1']])
        self.assertEqual(['z', 'y', 'x'], [t.id() for t in results['layer2']])

    def test_repeated_names(self):
        # Some doctests are run repeatedly with different scenarios.  They
        # have the same name but different testcases.  Those tests must not be
        # collapsed and lost.
        layername = 'layer-1'
        testnames = ['1', '2', '3']
        suite = unittest.suite.TestSuite()
        for t in testnames:
            # Each test will be repeated equal to the number represented.
            for i in range(int(t)):
                suite.addTest(FakeTestCase(t))
        with tempfile.NamedTemporaryFile() as fd:
            self.writeFile(fd, testnames)
            do_filter = filter_tests(fd.name)
            results = do_filter({layername: suite})
        self.assertEqual(1, len(results))
        self.assertTrue(layername in results)
        suite = results[layername]
        expected = ['1', '2', '2', '3', '3', '3']
        self.assertEqual(expected, [t.id() for t in suite])
