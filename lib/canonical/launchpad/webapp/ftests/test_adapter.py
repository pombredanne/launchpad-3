# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Run launchpad.database functional doctests"""

__metaclass__ = type

import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS

from canonical.functional import FunctionalLayer

def test_suite():
    suite = DocFileSuite('test_adapter.txt',
                     optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE|ELLIPSIS)
    suite.layer = FunctionalLayer
    return suite

