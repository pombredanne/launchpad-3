# Copyright 2006 Canonical Ltd.  All rights reserved.

import unittest

from zope.testing.doctest import DocTestSuite

from lp.bugs.browser import bugtask
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(bugtask))
    suite.addTest(LayeredDocFileSuite(
        'bugtask-target-link-titles.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
