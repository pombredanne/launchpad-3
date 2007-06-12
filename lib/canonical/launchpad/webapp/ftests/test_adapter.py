# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Run launchpad.database functional doctests"""

__metaclass__ = type

import unittest
from zope.testing.doctest import (
    DocFileSuite, REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS)

from canonical.testing import LaunchpadFunctionalLayer

def test_suite():
    suite = DocFileSuite(
        'test_adapter.txt',
        'reconnecting-adapter.txt',
        'reconnecting-adapter-zope-transaction.txt',
        optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE|ELLIPSIS)
    suite.layer = LaunchpadFunctionalLayer
    return suite

