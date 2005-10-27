# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import sys
import time
import unittest
import logging
from urllib2 import urlopen
from StringIO import StringIO

from zope.testing import doctest
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestSetup
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.functional import FunctionalTestSetup

import os.path

this_directory = os.path.dirname(__file__)

def setUp(test):
    # Suck this modules environment into the test environment
    test.globs.update(globals())

def tearDown(test):
    pass

def test_suite():
    return doctest.DocFileSuite(
            'librarianformatter_noca.txt', setUp=setUp, tearDown=tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
            )

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
