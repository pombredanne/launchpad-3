# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite

def test_suite():
    suite = unittest.TestSuite([DocFileSuite("filesystem.txt")])
    return suite

if __name__ == "__main__":
    unittest.main(defaultTest = "test_suite")
