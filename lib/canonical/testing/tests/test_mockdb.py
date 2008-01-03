# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Unit tests for the mockdb module."""

__metaclass__ = type
__all__ = []

import os
import os.path
import unittest

from canonical.testing import mockdb

class MockDbTestCase(unittest.TestCase):
    def setUp(self):
        self.cache_filename = mockdb.cache_filename('_mockdb_unittest')

    def tearDown(self):
        if os.path.exists(self.cache_filename):
            os.unlink(self.cache_filename)

    def testSerialize(self):
        # Ensure the caches can store and retrieve their logs
        recorder = mockdb.RecordCache(self.cache_filename)
        recorder.log = ['Arbitrary Data']
        recorder.store()

        replayer = mockdb.ReplayCache(self.cache_filename)
        self.failUnlessEqual(replayer.log, ['Arbitrary Data'])

    def testHandleInvalidCache(self):
        # Ensure a RetryTest exception is raised and the invalid cache
        # file removed when handleInvalidCache() is called
        recorder = mockdb.RecordCache(self.cache_filename)
        recorder.store()

        replayer = mockdb.ReplayCache(self.cache_filename)

        self.assertRaises(
                mockdb.RetryTest, replayer.handleInvalidCache, 'Reason'
                )
        self.failIf(os.path.exists(self.cache_filename))

    def testShortCache(self):
        # Ensure a RetryTest exception is raised if an attempt to pull
        # results from an exhausted cache.
        recorder = mockdb.RecordCache(self.cache_filename)
        recorder.store()
        replayer = mockdb.ReplayCache(self.cache_filename)
        self.assertRaises(mockdb.RetryTest, replayer.getNextEntry, None, None)

    def testCacheFilename(self):
        # Ensure evil characters in the key don't mess up the cache_filename
        # results. Only '/' is really evil - others chars should all work
        # fine but we might as well sanitise ones that might be annoying.
        evil_chars = ['/', ' ', '*', '?', '~', '\0']
        for key in evil_chars:
            path = mockdb.cache_filename(key)

            # Ensure our initial path is correct
            self.failUnlessEqual(
                    os.path.commonprefix([mockdb.CACHE_DIR, path]),
                    mockdb.CACHE_DIR
                    )

            # And there are no path segments
            self.failUnlessEqual(os.path.dirname(path), mockdb.CACHE_DIR)

            # And that the filename contains no evil or annoying characters
            filename = os.path.basename(path)
            for evil_char in evil_chars:
                self.failIf(evil_char in filename)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MockDbTestCase))
    return suite

