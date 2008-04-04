# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Run launchpad.database functional doctests"""

__metaclass__ = type

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer

# XXX: 2007-08-08 jamesh
# The adapter-serialization.txt test is disabled as it is getting
# spurious failures again and blocking other merges.
#    https://bugs.launchpad.net/bugs/131043

def test_suite():
    return LayeredDocFileSuite(
        'test_adapter.txt',
        #'adapter-serialization.txt',
        'reconnecting-adapter.txt',
        'reconnecting-adapter-zope-transaction.txt',
        layer=LaunchpadFunctionalLayer)

