# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running tests against IHasBugcontact
implementations.
"""

import unittest

from canonical.launchpad.interfaces.ftests. \
    test_structuralsubscriptiontarget import distributionSetUp, productSetUp
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    """Return the `IHasBugSupervisor` TestSuite."""
    suite = unittest.TestSuite()

    setUpMethods = [
        productSetUp,
        distributionSetUp,
        ]

    for setUpMethod in setUpMethods:
        test = LayeredDocFileSuite('has-bug-supervisor.txt',
            setUp=setUpMethod, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)

    return suite
