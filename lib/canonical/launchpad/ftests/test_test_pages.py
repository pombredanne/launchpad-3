# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Test that 

Set up the test data in the database first.
"""
__metaclass__ = type

import unittest
import shutil
import tempfile

from canonical.launchpad.ftests.test_pages import TestStory


class TestMakeStoryTest(unittest.TestCase):

    def setUp(self):
        # we need an empty story to test with.
        self.tempdir = tempfile.mkdtemp()
        unittest.TestCase.setUp(self)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.tempdir)
        
    def test_construction_and_trivial_running(self):
        story = TestStory(self.tempdir)
        self.failIf(isinstance(story, unittest.TestSuite))
        self.failUnless(isinstance(story, unittest.TestCase))
        result = unittest.TestResult()
        story.run(result)
        self.assertEqual(2, result.testsRun)
        self.assertEqual([], result.failures)
        self.assertEqual([], result.errors)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
