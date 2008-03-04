# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Runs the POFileTranslator test."""

__metaclass__ = type

import os.path

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
        'pofiletranslator.txt', layer=LaunchpadFunctionalLayer,
        setUp=setUp, tearDown=tearDown)
