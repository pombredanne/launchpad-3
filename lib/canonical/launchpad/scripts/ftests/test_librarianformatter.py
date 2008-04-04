# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

from datetime import datetime, timedelta
import logging
import os.path
import re
from StringIO import StringIO
import sys
import time
from urllib2 import urlopen

from pytz import utc
import transaction

from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer


this_directory = os.path.dirname(__file__)

def setUp(test):
    # Suck this modules environment into the test environment
    test.globs.update(globals())
    login(ANONYMOUS)

def tearDown(test):
    logout()

def test_suite():
    return LayeredDocFileSuite(
        'librarianformatter.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer)
