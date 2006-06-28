# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS

from canonical.testing.layers import Database

def test_suite():
    test_disconnects = DocFileSuite(
            'test_disconnects.txt',
            optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE
            )
    test_reconnector = DocFileSuite(
            'test_reconnector.txt',
            optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE
            )
    test_reconnector.layer = Database
    test_reconnect_already_closed = DocFileSuite(
            'test_reconnect_already_closed.txt',
            optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE
            )
    test_zopelesstransactionmanager = DocFileSuite(
            'test_zopelesstransactionmanager.txt',
            optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE
            )
    test_zopeless_reconnect = DocFileSuite(
            'test_zopeless_reconnect.txt',
            optionflags=ELLIPSIS|REPORT_NDIFF|NORMALIZE_WHITESPACE
            )
    suite = unittest.TestSuite([
        test_disconnects,
        test_reconnector,
        test_reconnect_already_closed,
        test_zopelesstransactionmanager,
        test_zopeless_reconnect,
        ])
    return suite

