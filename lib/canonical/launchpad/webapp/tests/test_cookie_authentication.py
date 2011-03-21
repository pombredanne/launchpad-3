# Copyright 2010 Canonical Ltd.  All rights reserved.

"""Test harness for running the cookie-authentication.txt tests."""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.testing.browser import (
    setUp,
    tearDown,
    )
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing.layers import AppServerLayer


def test_suite():
    suite = unittest.TestSuite()
    # We run this test on the AppServerLayer because it needs the cookie login
    # page (+login), which cannot be used through the normal testbrowser that
    # goes straight to zope's publication instead of making HTTP requests.
    suite.addTest(LayeredDocFileSuite(
        'cookie-authentication.txt', setUp=setUp, tearDown=tearDown,
        layer=AppServerLayer))
    return suite
