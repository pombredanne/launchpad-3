# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Test for rendering the time out OOPS page."""

__metaclass__ = type

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = LayeredDocFileSuite(
            'test_request_expire_render.txt',
            layer=LaunchpadFunctionalLayer, setUp=setUp, tearDown=tearDown,
            )
    return suite

