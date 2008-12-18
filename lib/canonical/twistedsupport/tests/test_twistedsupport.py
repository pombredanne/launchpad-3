# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from twisted.internet import defer

from canonical.twistedsupport import extract_result
from canonical.launchpad.testing import TestCase

class TestExtractResult(TestCase):

    def test_success(self):
        val = self.factory.getUniqueString()
        deferred = defer.succeed(val)
        self.assertEqual(val, extract_result(deferred))

    def test_failure(self):
        deferred = defer.fail(RuntimeError())
        self.assertRaises(RuntimeError, extract_result, deferred)

    def test_not_fired(self):
        deferred = defer.Deferred()
        self.assertRaises(AssertionError, extract_result, deferred)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

