# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test harness for running the questiontarget.txt interface test

This module will run the interface test against the Product, Distribution,
DistributionSourcePackage and SourcePackage implementations of that interface.
"""

__metaclass__ = type

__all__ = []

import unittest

from zope.component import getUtility

from canonical.functional import FunctionalDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.interfaces import IDistributionSet, IProductSet
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)


def productSetUp(test):
    setUp(test)
    test.globs['target'] = getUtility(IProductSet).getByName('thunderbird')


def distributionSetUp(test):
    setUp(test)
    test.globs['target'] = getUtility(IDistributionSet).getByName('kubuntu')


def sourcepackageSetUp(test):
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['target'] = ubuntu.currentseries.getSourcePackage('evolution')


def distributionsourcepackageSetUp(test):
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['target'] = ubuntu.getSourcePackage('evolution')


def test_suite():
    suite = unittest.TestSuite()

    targets = [('product', productSetUp),
               ('distribution', distributionSetUp),
               ('sourcepackage', sourcepackageSetUp),
               ('distributionsourcepackage', distributionsourcepackageSetUp),
               ]

    for name, setUpMethod in targets:
        test = FunctionalDocFileSuite('questiontarget.txt',
                    setUp=setUpMethod, tearDown=tearDown,
                    optionflags=default_optionflags, package=__name__,
                    layer=LaunchpadFunctionalLayer)
        suite.addTest(test)

    test = FunctionalDocFileSuite('questiontarget-sourcepackage.txt',
                setUp=setUp, tearDown=tearDown,
                optionflags=default_optionflags, package=__name__,
                layer=LaunchpadFunctionalLayer)
    suite.addTest(test)
    return suite


if __name__ == '__main__':
    unittest.main()
