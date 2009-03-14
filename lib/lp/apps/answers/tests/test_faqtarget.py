# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the faqtarget.txt interface test

This module will run the interface test against the Product and Distribution.
"""

__metaclass__ = type

__all__ = []

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces import IDistributionSet, IProductSet
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing.layers import DatabaseFunctionalLayer


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
        test = LayeredDocFileSuite('faqtarget.txt',
                    setUp=setUpMethod, tearDown=tearDown,
                    layer=DatabaseFunctionalLayer)
        suite.addTest(test)

    return suite

