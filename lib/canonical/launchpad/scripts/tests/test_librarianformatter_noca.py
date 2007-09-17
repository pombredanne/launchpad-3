# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from zope.testing import doctest
from canonical.testing import reset_logging

import os.path

this_directory = os.path.dirname(__file__)

def setUp(test):
    # Suck this modules environment into the test environment
    test.globs.update(globals())
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
