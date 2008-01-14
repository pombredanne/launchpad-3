# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Python harness for librarianformatter_noca.txt."""

__metaclass__ = type

import unittest

from zope.testing import doctest
from canonical.testing import reset_logging

def setUp(test):
    # Suck this modules environment into the test environment
    reset_logging()

def tearDown(test):
    reset_logging()

def test_suite():
    return doctest.DocFileSuite(
            'librarianformatter_noca.txt', setUp=setUp, tearDown=tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
            )

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
