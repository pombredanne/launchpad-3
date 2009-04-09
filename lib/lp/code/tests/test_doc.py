# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
Run the doctests and pagetests.
"""

import logging
import os
import unittest

from canonical.launchpad.testing.pages import PageTestSuite
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer)


here = os.path.dirname(os.path.realpath(__file__))


def zopelessLaunchpadSecuritySetUp(test):
    """Set up a LaunchpadZopelessLayer test to use LaunchpadSecurityPolicy.

    To be able to use LaunchpadZopelessLayer.switchDbUser in a test, we need
    to run in the Zopeless environment. The Zopeless environment normally runs
    using the PermissiveSecurityPolicy. If we want the test to cover
    functionality used in the webapp, it needs to use the
    LaunchpadSecurityPolicy.
    """
    setGlobs(test)
    test.old_security_policy = setSecurityPolicy(LaunchpadSecurityPolicy)


def zopelessLaunchpadSecurityTearDown(test):
    setSecurityPolicy(test.old_security_policy)


special = {
    'codeimport-machine.txt': LayeredDocFileSuite(
        '../doc/codeimport-machine.txt',
        setUp=zopelessLaunchpadSecuritySetUp,
        tearDown=zopelessLaunchpadSecurityTearDown,
        layer=LaunchpadZopelessLayer,
        ),
    'branch-merge-proposals.txt': LayeredDocFileSuite(
        '../doc/branch-merge-proposals.txt',
        setUp=zopelessLaunchpadSecuritySetUp,
        tearDown=zopelessLaunchpadSecurityTearDown,
        layer=LaunchpadZopelessLayer,
        ),
    }


def test_suite():
    suite = unittest.TestSuite()

    stories_dir = os.path.join(os.path.pardir, 'stories')
    suite.addTest(PageTestSuite(stories_dir))
    stories_path = os.path.join(here, stories_dir)
    for story_dir in os.listdir(stories_path):
        full_story_dir = os.path.join(stories_path, story_dir)
        if not os.path.isdir(full_story_dir):
            continue
        story_path = os.path.join(stories_dir, story_dir)
        suite.addTest(PageTestSuite(story_path))

    testsdir = os.path.abspath(
        os.path.normpath(os.path.join(here, os.path.pardir, 'doc'))
        )

    # Add tests using default setup/teardown
    filenames = [filename
                 for filename in os.listdir(testsdir)
                 if filename.endswith('.txt') and filename not in special]
    # Sort the list to give a predictable order.
    filenames.sort()
    for filename in filenames:
        path = os.path.join('../doc/', filename)
        one_test = LayeredDocFileSuite(
            path, setUp=setUp, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
            stdout_logging_level=logging.WARNING
            )
        suite.addTest(one_test)

    return suite
