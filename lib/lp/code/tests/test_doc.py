# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import os

from zope.security.management import setSecurityPolicy

from canonical.config import config
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setGlobs,
    setUp,
    tearDown,
    )
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))


def branchscannerSetUp(test):
    """Setup the user for the branch scanner tests."""
    LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
    setUp(test)


def zopelessLaunchpadSecuritySetUp(test):
    """Set up a LaunchpadZopelessLayer test to use LaunchpadSecurityPolicy.

    To be able to use LaunchpadZopelessLayer.switchDbUser in a test, we need
    to run in the Zopeless environment. The Zopeless environment normally runs
    using the LaunchpadPermissiveSecurityPolicy. If we want the test to cover
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
    'revision.txt': LayeredDocFileSuite(
        '../doc/revision.txt',
        setUp=branchscannerSetUp, tearDown=tearDown,
        layer=LaunchpadZopelessLayer
        ),
    'codeimport-result.txt': LayeredDocFileSuite(
        '../doc/codeimport-result.txt',
        setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer,
        ),
    'branch-merge-proposal-notifications.txt': LayeredDocFileSuite(
        '../doc/branch-merge-proposal-notifications.txt',
        setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer,
        ),
    }


def test_suite():
    return build_test_suite(here, special)
