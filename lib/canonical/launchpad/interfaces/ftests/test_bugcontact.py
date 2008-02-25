# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for running tests against IHasBugcontact
implementations.
"""

import unittest

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.interfaces.ftests. \
    test_structuralsubscriptiontarget import distributionSetUp, productSetUp
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    """Return the `IHasBugcontact` TestSuite."""
    suite = unittest.TestSuite()

    setUpMethods = [
        productSetUp,
        distributionSetUp,
        ]

    for setUpMethod in setUpMethods:
        test = FunctionalDocFileSuite('has-bug-contact.txt',
            setUp=setUpMethod, tearDown=tearDown,
            optionflags=default_optionflags, package=__name__,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)

    return suite
