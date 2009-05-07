# Copyright 2009 Canonical Ltd.  All rights reserved.

import unittest

from zope.testing.doctest import DocTestSuite

from canonical.launchpad.browser import bugtask
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(LayeredDocFileSuite(
        'bug-portlet-subscribers-content.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

