# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite


# The setUp() and tearDown() functions ensure that this doctest is not umask
# dependent.
def setUp(testobj):
    testobj._old_umask = os.umask(022)


def tearDown(testobj):
    os.umask(testobj._old_umask)


def test_suite():
    suite = unittest.TestSuite([DocFileSuite("filesystem.txt",
                                             setUp=setUp, tearDown=tearDown)])
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest = "test_suite")
