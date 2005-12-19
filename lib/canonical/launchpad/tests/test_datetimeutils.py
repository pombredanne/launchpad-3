# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest

from zope.testing.doctest import DocTestSuite

from canonical.launchpad import datetimeutils


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(datetimeutils))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

