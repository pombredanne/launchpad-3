# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for LAZR doctests."""

__metaclass__ = type
__all__ = []

import os

from zope.testing.cleanup import cleanUp

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite

def tearDown(test):
    """Run registered clean-up function."""
    cleanUp()


def test_suite():
    """See `zope.testing.testrunner`."""
    tests = sorted(
        ['../doc/%s' % name
         for name in os.listdir(
            os.path.join(os.path.dirname(__file__), '../doc'))
         if name.endswith('.txt')])
    return LayeredDocFileSuite(
        stdout_logging=False, tearDown=tearDown, *tests)
