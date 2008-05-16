# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test related to ExternalBugtracker test infrastructure."""

__metaclass__ = type

__all__ = []

from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)


def test_suite():
    return LayeredDocFileSuite(
        'bugzilla-xmlrpc-transport.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer)
    return LayeredDocFileSuite(
        'trac-xmlrpc-transport.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer)
