# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Run launchpad.database functional doctests"""

__metaclass__ = type

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer

def test_suite():
    return LayeredDocFileSuite(
        'test_adapter.txt',
        layer=LaunchpadFunctionalLayer)

