# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for LAZR doctests."""

__metaclass__ = type
__all__ = []

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite


def test_suite():
    """See `zope.testing.testrunner`."""
    return LayeredDocFileSuite(
        '../doc/debug.txt',
        '../doc/decorates.txt',
        '../doc/checker-utilities.txt',
        '../doc/config.txt',
        '../doc/interface.txt',
        '../doc/menus.txt',
        '../doc/webservice-declarations.txt',
        stdout_logging=False)

