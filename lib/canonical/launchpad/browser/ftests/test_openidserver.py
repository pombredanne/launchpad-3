# Copyright 2007 Canonical Ltd.  All rights reserved.

import unittest, doctest

from canonical.testing import LaunchpadZopelessLayer

def test_suite():
    suite = unittest.TestSuite()
    suite.layer = LaunchpadZopelessLayer
    suite.addTest(doctest.DocTestSuite(
        'canonical.launchpad.browser.openidserver'
        ))
    return suite

