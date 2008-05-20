# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for LAZR doctests."""

__metaclass__ = type
__all__ = []

import os

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite

def test_suite():
    """See `zope.testing.testrunner`."""
    tests = sorted(
        ['../doc/%s' % name
         for name in os.listdir(
            os.path.join(os.path.dirname(__file__), '../doc'))
         if name.endswith('.txt')])
    return LayeredDocFileSuite(stdout_logging=False, *tests)
