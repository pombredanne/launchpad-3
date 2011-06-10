# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running the bugtarget-recently-touched-bugs.txt tests.

This module will run the tests against the all the current IBugTarget
implementations.
"""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    tearDown,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.bugs.tests.test_bugtarget import (
    distributionSeriesSetUp,
    distributionSetUp,
    distributionSourcePackageSetUp,
    productSeriesSetUp,
    productSetUp,
    projectSetUp,
    sourcePackageSetUp,
    )


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
        test = LayeredDocFileSuite(
            'special/bugtarget-recently-touched-bugs.txt',
            setUp=setUpMethod, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)
    return suite
