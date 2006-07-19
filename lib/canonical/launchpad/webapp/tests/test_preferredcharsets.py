# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Tests for choosing the preferred charsets."""

__metaclass__ = type

import unittest

from zope.testing.doctest import (
    DocFileSuite, REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS)


def test_suite():
    suite = unittest.TestSuite([
        DocFileSuite(
            'test_preferredcharsets.txt',
            optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE|ELLIPSIS)
        ])
    return suite

