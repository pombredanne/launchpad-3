# Copyright 2006 Canonical Ltd.  All rights reserved.

import unittest

from zope.testing.doctest import DocTestSuite

from canonical.launchpad.browser import logintoken


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(logintoken))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

