# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test related to ExternalBugtracker test infrastructure."""

__metaclass__ = type

__all__ = []

import unittest

from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(LayeredDocFileSuite(
        'bugzilla-xmlrpc-transport.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer))
    suite.addTest(LayeredDocFileSuite(
        'trac-xmlrpc-transport.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer))

    return suite
