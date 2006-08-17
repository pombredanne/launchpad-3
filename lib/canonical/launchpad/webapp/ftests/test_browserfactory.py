# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Test for choosing the request and publication."""

__metaclass__ = type

import unittest
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS

from canonical.functional import FunctionalDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = FunctionalDocFileSuite(
            'launchpad/webapp/ftests/test_browserfactory.txt',
            optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE|ELLIPSIS,
            layer=LaunchpadFunctionalLayer
            )
    return suite

