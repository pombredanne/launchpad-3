# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for running tests against IStructuralsubscriptionTarget
implementations.
"""

import unittest

from zope.component import getUtility

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.interfaces import (
    IDistributionSet, IProductSet)
from canonical.launchpad.interfaces.ftests.test_bugtarget import (
    bugtarget_filebug)
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer

def distributionSourcePackageSetUp(test):
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['target'] = ubuntu.getSourcePackage('evolution')
    test.globs['other_target'] = ubuntu.getSourcePackage('pmount')
    test.globs['filebug'] = bugtarget_filebug

def productSetUp(test):
    setUp(test)
    test.globs['target'] = getUtility(IProductSet).getByName('firefox')
    test.globs['filebug'] = bugtarget_filebug

def test_suite():
    """Return the `IStructuralSubscriptionTarget` TestSuite."""
    suite = unittest.TestSuite()

    setUpMethods = [
        distributionSourcePackageSetUp,
        productSetUp,
        ]

    for setUpMethod in setUpMethods:
        test = FunctionalDocFileSuite('structural-subscription-target.txt',
            setUp=setUpMethod, tearDown=tearDown,
            optionflags=default_optionflags, package=__name__,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)

    return suite
