# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for things found directly in `canonical.twistedsupport`."""

__metaclass__ = type

import unittest

from twisted.internet import defer

from canonical.twistedsupport import extract_result
from lp.testing import TestCase

class TestExtractResult(TestCase):
    """Tests for `canonical.twisted_support.extract_result`."""

    def test_success(self):
        # extract_result on a Deferred that has a result returns the result.
        val = self.factory.getUniqueString()
        deferred = defer.succeed(val)
        self.assertEqual(val, extract_result(deferred))

    def test_failure(self):
        # extract_result on a Deferred that has an error raises the failing
        # exception.
        deferred = defer.fail(RuntimeError())
        self.assertRaises(RuntimeError, extract_result, deferred)

    def test_not_fired(self):
        # extract_result on a Deferred that has not fired raises
        # AssertionError (extract_result is only supposed to be used when you
        # _know_ that the API you're using is really synchronous, despite
        # returning deferreds).
        deferred = defer.Deferred()
        self.assertRaises(AssertionError, extract_result, deferred)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

