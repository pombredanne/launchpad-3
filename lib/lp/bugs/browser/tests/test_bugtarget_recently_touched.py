# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test harness for running the bugtarget-recently-touched-bugs.txt tests.

This module will run the tests against the all the current IBugTarget
implementations.
"""

__metaclass__ = type

__all__ = []

import unittest

from lp.bugs.tests.test_bugtarget import (
    distributionSetUp, distributionSeriesSetUp,
    distributionSourcePackageSetUp,  productSetUp, productSeriesSetUp,
    projectSetUp, sourcePackageSetUp)
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = unittest.TestSuite()

    setUpMethods = [
        productSetUp,
        productSeriesSetUp,
        projectSetUp,
        distributionSetUp,
        distributionSourcePackageSetUp,
        distributionSeriesSetUp,
        sourcePackageSetUp,
        ]

    for setUpMethod in setUpMethods:
        test = LayeredDocFileSuite('bugtarget-recently-touched-bugs.txt',
            setUp=setUpMethod, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)
    return suite
