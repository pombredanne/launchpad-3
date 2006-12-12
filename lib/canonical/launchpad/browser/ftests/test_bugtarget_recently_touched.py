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
    IProductSet, IDistributionSet)
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer

def productSetUp(test):
    setUp(test)
    test.globs['bugtarget'] = getUtility(IProductSet).getByName('firefox')


def distributionSetUp(test):
    setUp(test)
    test.globs['bugtarget'] = getUtility(IDistributionSet).getByName('ubuntu')


def fooSetUp(test):
    setUp(test)
    test.globs['target'] = getUtility(ISpecificationSet).getByURL(
        'http://wiki.mozilla.org/Firefox:1.1_Product_Team')


def test_suite():
    suite = unittest.TestSuite()

    bugtargets = [
        ('product', productSetUp),
        ('distribution', distributionSetUp)]

    for name, setUpMethod in bugtargets:
        test = FunctionalDocFileSuite('bugtarget-recently-touched-bugs.txt',
            setUp=setUpMethod, tearDown=tearDown,
            optionflags=default_optionflags, package=__name__,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)
    return suite


if __name__ == '__main__':
    unittest.main()
