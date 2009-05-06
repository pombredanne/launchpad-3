# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
Run the view tests.
"""

import logging
import os
import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


here = os.path.dirname(os.path.realpath(__file__))


def test_suite():
    suite = unittest.TestSuite()
    testsdir = os.path.abspath(here)

    # Tests that are special and take care of their own harnessing.
    special_tests = ['shipit-login.txt']

    # Add tests using default setup/teardown
    filenames = [
        filename for filename in os.listdir(testsdir)
        if filename.endswith('.txt') and filename not in special_tests]
    # Sort the list to give a predictable order.
    filenames.sort()
    for filename in filenames:
        path = filename
        one_test = LayeredDocFileSuite(
            path, setUp=setUp, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
            stdout_logging_level=logging.WARNING
            )
        suite.addTest(one_test)

    return suite
