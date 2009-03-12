# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test harness for running the shipit-login.txt tests."""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.testing.pages import setUpGlobs
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing.layers import AppServerLayer


def customSetUp(test):
    setUp(test)
    setUpGlobs(test)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(LayeredDocFileSuite(
        'shipit-login.txt', setUp=customSetUp, tearDown=tearDown,
        layer=AppServerLayer))
    return suite
