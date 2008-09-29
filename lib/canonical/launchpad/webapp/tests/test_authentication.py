# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Tests authentication.py"""

__metaclass__ = type

__all__ = [
    'test_suite',
    ]


from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = LayeredDocFileSuite(
            'test_launchpad_login_source.txt',
            layer=LaunchpadFunctionalLayer, setUp=setUp, tearDown=tearDown,
            )
    return suite

