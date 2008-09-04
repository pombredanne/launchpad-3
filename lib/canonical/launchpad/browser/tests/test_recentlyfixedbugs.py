# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for running the recently-fixed-bugs.txt tests."""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite


def test_suite():
    suite = unittest.TestSuite()
    test = LayeredDocFileSuite('recently-fixed-bugs.txt')
    suite.addTest(test)
    return suite
