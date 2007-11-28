# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test harness for running the bugtarget-recently-touched-bugs.txt tests.

This module will run the tests against the all the current IBugTarget
implementations.
"""

__metaclass__ = type

__all__ = []

import unittest

from zope.component import getUtility

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.interfaces import (
    CreateBugParams, IBugTaskSet, IDistributionSet, ILaunchBag, IProductSet,
    IProjectSet)
from canonical.launchpad.interfaces.ftests.test_bugtarget import (
    bugtarget_filebug, productSetUp, project_filebug, projectSetUp,
    productseries_filebug, productSeriesSetUp, distributionSetUp,
    distributionSourcePackageSetUp, distroseries_filebug,
    distributionSeriesSetUp, sourcepackage_filebug, sourcePackageSetUp)
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)
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
        test = FunctionalDocFileSuite('bugtarget-recently-touched-bugs.txt',
            setUp=setUpMethod, tearDown=tearDown,
            optionflags=default_optionflags, package=__name__,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)
    return suite
