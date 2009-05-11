# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
A standard test suite for

Assumes the following layout beneath base_dir:

 stories/ - Contains pagetests
 doc/ - Contains doctests
"""

import logging
import os
import unittest

from zope.testing import doctest

from canonical.launchpad.testing.pages import PageTestSuite
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.testing.systemdocs import strip_prefix

def build_test_suite(base_dir, special_tests={},
                     layer=LaunchpadFunctionalLayer,
                     setUp=setUp, tearDown=tearDown):
    """Build a test suite from a directory containing test files.

    The 'stories' subdirectory will be checked for pagetests and the
    'doc' subdirectory will be checked for doctests.

    :param base_dir: The directory to check for tests.

    :param special_tests: A dict mapping filenames to TestSuite
    objects. These files need special treatment (for instance, they
    should be run in a different layer, or they need custom
    setup/teardown). The given TestSuite object will be used for that
    file, rather than a new one generated.

    :param layer: The layer in which to run the tests.
    """
    suite = unittest.TestSuite()

    # Tests are run relative to the calling module, not this module.
    package = doctest._normalize_module(None)

    # Add the pagetests.
    stories_dir = os.path.join(os.path.pardir, 'stories')
    stories_path = os.path.join(base_dir, stories_dir)
    if os.path.exists(stories_path):
        suite.addTest(PageTestSuite(stories_dir, package))
        for story_dir in os.listdir(stories_path):
            full_story_dir = os.path.join(stories_path, story_dir)
            if not os.path.isdir(full_story_dir):
                continue
            story_path = os.path.join(stories_dir, story_dir)
            suite.addTest(PageTestSuite(story_path, package))

    # Add the special doctests.
    for key in sorted(special_tests):
        special_suite = special_tests[key]
        suite.addTest(special_suite)

    tests_path = os.path.join(os.path.pardir, 'doc')
    testsdir = os.path.abspath(
        os.path.normpath(os.path.join(base_dir, tests_path))
        )

    if os.path.exists(testsdir):
        # Add doctests using default setup/teardown
        filenames = [filename
                     for filename in os.listdir(testsdir)
                     if (filename.endswith('.txt')
                         and filename not in special_tests)]
        # Sort the list to give a predictable order.
        filenames.sort()
        for filename in filenames:
            path = os.path.join(tests_path, filename)
            one_test = LayeredDocFileSuite(
                path, package=package, setUp=setUp, tearDown=tearDown,
                layer=layer, stdout_logging_level=logging.WARNING
                )
            suite.addTest(one_test)

    return suite
