# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Test for choosing the request and publication."""

__metaclass__ = type

from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS

from canonical.functional import FunctionalDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.ftests.test_system_documentation import (
    setUp, tearDown)

def test_suite():
    suite = FunctionalDocFileSuite(
            'test_bugtask_status.txt',
            optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE|ELLIPSIS,
            layer=LaunchpadFunctionalLayer, setUp=setUp, tearDown=tearDown,
            )
    return suite

