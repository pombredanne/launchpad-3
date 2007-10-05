# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the faqtarget.txt interface test

This module will run the interface test against the Product and Distribution.
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


def test_suite():
    suite = unittest.TestSuite()

    targets = [('product', productSetUp),
               ('distribution', distributionSetUp),
               ]

    for name, setUpMethod in targets:
        test = FunctionalDocFileSuite('faqtarget.txt',
                    setUp=setUpMethod, tearDown=tearDown,
                    optionflags=default_optionflags, package=__name__,
                    layer=LaunchpadFunctionalLayer)
        suite.addTest(test)

    return suite

