# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Unit tests for the mockdb module."""

__metaclass__ = type
__all__ = []

import os
import os.path
import unittest

from zope.testing.doctestunit import DocTestSuite

from canonical.testing import mockdb
from canonical.testing.mockdb import dont_retry, RetryTest


class MockDbTestCase(unittest.TestCase):
    def setUp(self):
        self.cache_filename = mockdb.cache_filename('_mockdb_unittest')

    def tearDown(self):
        if os.path.exists(self.cache_filename):
            os.unlink(self.cache_filename)

    @dont_retry
    def testSerialize(self):
        # Ensure the caches can store and retrieve their logs
        recorder = mockdb.RecordCache(self.cache_filename)
        recorder.log = ['Arbitrary Data']
        recorder.store()

        replayer = mockdb.ReplayCache(self.cache_filename)
        self.failUnlessEqual(replayer.log, ['Arbitrary Data'])

    @dont_retry
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

    @dont_retry
    def testShortCache(self):
        # Ensure a RetryTest exception is raised if an attempt to pull
        # results from an exhausted cache.
        recorder = mockdb.RecordCache(self.cache_filename)
        recorder.store()
        replayer = mockdb.ReplayCache(self.cache_filename)
        self.assertRaises(mockdb.RetryTest, replayer.getNextEntry, None, None)

    @dont_retry
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

    _retry_count = 0

    # This test needs to leak RetryTest exeptions as it tests that the
    # test runner is handling them correctly.
    #@dont_retry
    def testRetryTestRetriesTest(self):
        MockDbTestCase._retry_count += 1
        if MockDbTestCase._retry_count % 2 == 1:
            raise RetryTest("Testing RetryTest behavior")


_doctest_retry_count = 0

def retry_on_odd_numbered_calls():
    """Helper for doctest RetryTest test.
    
    >>> try:
    ...     retry_on_odd_numbered_calls()
    ... except RetryTest:
    ...     print "Caught RetryTest."
    ...
    Retry raised.
    Caught RetryTest.
    >>> try:
    ...     retry_on_odd_numbered_calls()
    ... except RetryTest:
    ...     print "Caught RetryTest."
    ...
    Retry not raised.
    """
    global _doctest_retry_count
    _doctest_retry_count += 1
    if _doctest_retry_count % 2 == 1:
        print "Retry raised."
        raise RetryTest
    print "Retry not raised."


def testRetryTestInDoctest():
    """Test a RetryTest exception in a doctest works as expected.

    The first time this doctest is run, the following call will raise
    a RetryTest exception. You shouldn't see this though, as the test
    machinery will silently retry the test and the second time through
    the method will not raise this exception (well - you might see the test
    runner report that it is running this test twice because refactoring the
    testrunner and unittest framework and maintaining the patch to support
    Retry properly is just way too much work for little gain).

    >>> retry_on_odd_numbered_calls()
    Retry not raised.
    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MockDbTestCase))
    suite.addTest(DocTestSuite())
    return suite

