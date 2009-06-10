# Copyright 2004-2009 Canonical Ltd.  All rights reserved.

"""Runs the doctests for buildmaster module."""

__metaclass__ = type


import logging
import os
import unittest

from canonical.config import config
from canonical.launchpad.ftests import login, logout, ANONYMOUS
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setGlobs)
from canonical.testing import LaunchpadZopelessLayer


def setUp(test):
    """Setup a typical builddmaster test environment.

    Log in as ANONYMOUS and perform DB operations as the builddmaster
    dbuser.
    """
    test_dbuser = config.builddmaster.dbuser
    login(ANONYMOUS)
    setGlobs(test)
    test.globs['test_dbuser'] = test_dbuser
    LaunchpadZopelessLayer.switchDbUser(test_dbuser)


def tearDown(test):
    logout()


def test_suite():
    """Load doctests in this directory.

    Use `LayeredDocFileSuite` with the custom `setUp` and tearDown`,
    suppressed logging messages (only warnings and errors will be posted)
    on `LaunchpadZopelessLayer`.
    """
    suite = unittest.TestSuite()
    tests_dir = os.path.dirname(os.path.realpath(__file__))

    filenames = [
        filename
        for filename in os.listdir(tests_dir)
        if filename.lower().endswith('.txt')
        ]

    for filename in sorted(filenames):
        test = LayeredDocFileSuite(
            filename, setUp=setUp, tearDown=tearDown,
            stdout_logging_level=logging.WARNING,
            layer=LaunchpadZopelessLayer)
        suite.addTest(test)

    return suite
