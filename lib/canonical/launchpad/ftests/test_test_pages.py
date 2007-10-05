# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Test that creating page test stories from files and directories work."""
__metaclass__ = type

import os
import unittest
import shutil
import tempfile

from canonical.testing import PageTestLayer
from canonical.launchpad.ftests.test_pages import PageTestSuite

class TestMakeStoryTest(unittest.TestCase):
    layer = PageTestLayer

    def setUp(self):
        # we need an empty story to test with, and it has to be in the
        # testing namespace
        self.tempdir = tempfile.mkdtemp(dir=os.path.dirname(__file__))
        unittest.TestCase.setUp(self)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.tempdir)

    def test_dir_construction_and_trivial_running(self):
        test_filename = os.path.join(self.tempdir, '10-foo.txt')
        test_file = open(test_filename, 'wt')
        test_file.close()
        test_filename = os.path.join(self.tempdir, '20-bar.txt')
        test_file = open(test_filename, 'wt')
        test_file.close()
        test_filename = os.path.join(self.tempdir, 'xx-bar.txt')
        test_file = open(test_filename, 'wt')
        test_file.close()
        # The test directory is looked up relative to the calling
        # module's path.
        suite = PageTestSuite(os.path.basename(self.tempdir))
        self.failUnless(isinstance(suite, unittest.TestSuite))
        [bar_test, story] = list(suite)

        # The unnumbered file appears as an independent test.
        self.assertEqual(os.path.basename(bar_test.id()), 'xx-bar_txt')

        # The two numbered tests become a story, which appears as a
        # single test case rather than a test suite.
        self.failIf(isinstance(story, unittest.TestSuite))
        self.failUnless(isinstance(story, unittest.TestCase))
        result = unittest.TestResult()
        story.run(result)
        self.assertEqual(2, result.testsRun)
        self.assertEqual([], result.failures)
        self.assertEqual([], result.errors)


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)
    return suite
