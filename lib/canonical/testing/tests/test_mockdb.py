# Copyright 2007-2008 Canonical Ltd.  All rights reserved.

"""Unit tests for the mockdb module."""

__metaclass__ = type
__all__ = []

import os
import os.path
import unittest

from zope.testing.doctestunit import DocTestSuite
from zope.testing.testrunner import dont_retry, RetryTest

from canonical.testing import mockdb

class MockDbTestCase(unittest.TestCase):
    def setUp(self):
        self.script_filename = mockdb.script_filename('_mockdb_unittest')

    def tearDown(self):
        if os.path.exists(self.script_filename):
            os.unlink(self.script_filename)

    @dont_retry
    def testSerialize(self):
        # Ensure the scripts can store and retrieve their logs
        recorder = mockdb.ScriptRecorder(self.script_filename)
        recorder.log = ['Arbitrary Data']
        recorder.store()

        replayer = mockdb.ScriptPlayer(self.script_filename)
        self.failUnlessEqual(replayer.log, ['Arbitrary Data'])

    @dont_retry
    def testHandleInvalidScript(self):
        # Ensure a RetryTest exception is raised and the invalid script
        # file removed when handleInvalidScript() is called
        recorder = mockdb.ScriptRecorder(self.script_filename)
        recorder.store()

        replayer = mockdb.ScriptPlayer(self.script_filename)

        self.assertRaises(
                RetryTest, replayer.handleInvalidScript, 'Reason'
                )
        self.failIf(os.path.exists(self.script_filename))

    @dont_retry
    def testShortScript(self):
        # Ensure a RetryTest exception is raised if an attempt to pull
        # results from an exhausted script.
        recorder = mockdb.ScriptRecorder(self.script_filename)
        recorder.store()
        replayer = mockdb.ScriptPlayer(self.script_filename)
        self.assertRaises(RetryTest, replayer.getNextEntry, None, None)

    @dont_retry
    def testScriptFilename(self):
        # Ensure evil characters in the key don't mess up the script_filename
        # results. Only '/' is really evil - others chars should all work
        # fine but we might as well sanitise ones that might be annoying.
        evil_chars = ['/', ' ', '*', '?', '~', '\0']
        for key in evil_chars:
            path = mockdb.script_filename(key)

            # Ensure our initial path is correct
            self.failUnlessEqual(
                    os.path.commonprefix([mockdb.SCRIPT_DIR, path]),
                    mockdb.SCRIPT_DIR
                    )

            # And there are no path segments
            self.failUnlessEqual(os.path.dirname(path), mockdb.SCRIPT_DIR)

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

    This test confirms that a RetryException raised where no exception
    was expected works.

    >>> retry_on_odd_numbered_calls()
    Retry not raised.
    """


def retry_on_odd_numbered_calls2():
    """Helper for doctest RetryTest test.
    
    >>> try:
    ...     retry_on_odd_numbered_calls2()
    ... except RetryTest:
    ...     print "Caught RetryTest."
    ...
    Retry raised.
    Caught RetryTest.
    >>> try:
    ...     retry_on_odd_numbered_calls2()
    ... except RetryTest:
    ...     print "Caught RetryTest."
    ...
    Traceback (most recent call last):
    ...
    RuntimeError: Retry not raised.
    """
    global _doctest_retry_count
    _doctest_retry_count += 1
    if _doctest_retry_count % 2 == 1:
        print "Retry raised."
        raise RetryTest
    raise RuntimeError("Retry not raised.")


def testRetryTestInDoctest2():
    """Test a RetryTest exception in a doctest works as expected.

    This test is the same as testRetryTestInDoctest, except it confirms
    that a RetryException raised where a different exception was expected
    works.

    >>> retry_on_odd_numbered_calls2()
    Traceback (most recent call last):
    ...
    RuntimeError: Retry not raised.
    """



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MockDbTestCase))
    suite.addTest(DocTestSuite())
    return suite

