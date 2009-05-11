# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
Run the doctests and pagetests.
"""

import logging
import os
import unittest

from canonical.launchpad.testing.pages import PageTestSuite
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setGlobs, setUp, tearDown)
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer)

from lp.services.testing import build_test_suite


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
    return build_test_suite(here, special)
