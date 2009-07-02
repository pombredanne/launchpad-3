# Copyright 2006-2009 Canonical Ltd.  All rights reserved.

import unittest

from zope.testing.doctest import DocTestSuite

from canonical.launchpad.browser import authtoken


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(authtoken))
    return suite
