# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from zope.testing.doctest import DocFileSuite, DocTestSuite

def test_suite():
    suite = unittest.TestSuite((
        DocFileSuite("zodb_password_resets.txt", globs = {}),
        DocTestSuite("canonical.auth.browser")
        ))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest = "test_suite")
