# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import re
import sys
import time
import unittest
import logging
from urllib2 import urlopen
from StringIO import StringIO
from datetime import datetime, timedelta
from pytz import utc

import transaction
from zope.testing import doctest
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.testing import LaunchpadFunctionalLayer

import os.path

this_directory = os.path.dirname(__file__)

def setUp(test):
    # Suck this modules environment into the test environment
    test.globs.update(globals())
    login(ANONYMOUS)

def tearDown(test):
    logout()

def test_suite():
    suite = doctest.DocFileSuite(
            'librarianformatter.txt', setUp=setUp, tearDown=tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
            )
    suite.layer = LaunchpadFunctionalLayer
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
