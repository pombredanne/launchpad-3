# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import logging
import os.path
import re
from StringIO import StringIO
import sys
import time
from urllib2 import urlopen

from pytz import utc
import transaction

from lp.testing import (
    ANONYMOUS,
    login,
    logout,
    )
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.systemdocs import LayeredDocFileSuite


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
