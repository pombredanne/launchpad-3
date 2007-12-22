# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Unit tests for the mockdb module."""

__metaclass__ = type
__all__ = []

import os
import unittest

from canonical.testing import mockdb

class MockDbTestCase(unittest.TestCase):
    def setUp(self):
        self.cache_filename = mockdb.cache_filename('_mockdb_unittest')

    def tearDown(self):
        if os.path.exists(self.cache_filename):
            os.unlink(self.cache_filename)

    def test_serialize(self):
        # Ensure the caches can store and retrieve their logs
        recorder = mockdb.RecordCache(self.cache_filename)
        recorder.log = 'Arbitrary Data'
        recorder.store()

        replayer = mockdb.ReplayCache(self.cache_filename)
        self.failUnlessEqual(replayer.log, 'Arbitrary Data')

    def test_handleInvalidCache(self):
        # Ensure a RetryTest exception is raised and the invalid cache
        # file removed when handleInvalidCache() is called
        recorder = mockdb.RecordCache(self.cache_filename)
        recorder.store()

        replayer = mockdb.ReplayCache(self.cache_filename)

        self.assertRaises(
                mockdb.RetryTest, replayer.handleInvalidCache, 'Reason'
                )
        self.failIf(os.path.exists(self.cache_filename))

    def test_short_cache(self):
        # Ensure a RetryTest exception is raised if an attempt to pull
        # results from an exhausted cache.
        recorder = mockdb.RecordCache(self.cache_filename)
        recorder.store()
        replayer = mockdb.ReplayCache(self.cache_filename)
        self.assertRaises(mockdb.RetryTest, replayer.getNextEntry, None, None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MockDbTestCase))
    return suite

