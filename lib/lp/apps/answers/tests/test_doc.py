# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
Run the doctests and pagetests.
"""

import logging
import os
import unittest

from zope.component import getUtility

from canonical.launchpad.testing.pages import PageTestSuite
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import DatabaseFunctionalLayer


here = os.path.dirname(os.path.realpath(__file__))

def test_suite():
    suite = unittest.TestSuite()

    pagetests_dir = os.path.join(os.path.pardir, 'pagetests')
    suite.addTest(PageTestSuite(pagetests_dir))

    testsdir = os.path.abspath(
            os.path.normpath(os.path.join(here, os.path.pardir, 'doc'))
            )

    # Add tests using default setup/teardown
    filenames = [filename
                 for filename in os.listdir(testsdir)
                 if filename.lower().endswith('.txt')
                 ]
    # Sort the list to give a predictable order.
    filenames.sort()
    for filename in filenames:
        path = os.path.join('../doc/', filename)
        one_test = LayeredDocFileSuite(
            path, setUp=setUp, tearDown=tearDown,
            layer=DatabaseFunctionalLayer,
            stdout_logging_level=logging.WARNING
            )
        suite.addTest(one_test)

    return suite
