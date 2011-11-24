# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running tests against IHasBugcontact
implementations.
"""

import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    tearDown,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.tests.test_structuralsubscriptiontarget import (
    distributionSetUp,
    productSetUp,
    )


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
            layer=DatabaseFunctionalLayer)
        suite.addTest(test)

    return suite
