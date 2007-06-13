# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from zope.testing.doctest import DocFileSuite
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS

from canonical.testing import DatabaseLayer, LaunchpadLayer


def LayeredDocFileSuite(*args, **kw):
    layer = kw.pop('layer')
    suite = DocFileSuite(*args, **kw)
    suite.layer = layer
    return suite


def test_suite():
    optionflags = REPORT_NDIFF|NORMALIZE_WHITESPACE|ELLIPSIS
    return unittest.TestSuite([
            LayeredDocFileSuite(
                'test_disconnects.txt', layer=DatabaseLayer,
                optionflags=optionflags
                ),
            LayeredDocFileSuite(
                'test_multitablecopy.txt', layer=DatabaseLayer,
                optionflags=optionflags
                ),
            LayeredDocFileSuite(
                'test_reconnector.txt', layer=DatabaseLayer,
                optionflags=optionflags
                ),
            LayeredDocFileSuite(
                'test_reconnect_already_closed.txt', layer=DatabaseLayer,
                optionflags=optionflags
                ),
            LayeredDocFileSuite(
                'test_zopelesstransactionmanager.txt', layer=LaunchpadLayer,
                optionflags=optionflags
                ),
            LayeredDocFileSuite(
                'test_zopeless_reconnect.txt', layer=LaunchpadLayer,
                optionflags=optionflags
                ),
            ])

