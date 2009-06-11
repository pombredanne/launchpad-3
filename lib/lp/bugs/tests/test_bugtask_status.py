# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Test for choosing the request and publication."""

__metaclass__ = type

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = LayeredDocFileSuite(
            'test_bugtask_status.txt',
            layer=LaunchpadFunctionalLayer, setUp=setUp, tearDown=tearDown,
            )
    return suite

