# Copyright 2008 Canonical Ltd.  All rights reserved.

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
    """Return the `IHasBugcontact` TestSuite."""
    suite = unittest.TestSuite()

    setUpMethods = [
        productSetUp,
        distributionSetUp,
        ]

    for setUpMethod in setUpMethods:
        test = LayeredDocFileSuite('has-bug-contact.txt',
            setUp=setUpMethod, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)

    return suite
