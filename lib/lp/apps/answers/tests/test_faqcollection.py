# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the faqcollection.txt interface test

This module will run the interface test against Product, Distribution,
and Project.
"""

__metaclass__ = type

__all__ = []

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.interfaces import (
    IDistributionSet, IProductSet, IProjectSet)
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing.layers import DatabaseFunctionalLayer


def productSetUp(test):
    """Test environment for product."""
    setUp(test)
    thunderbird = getUtility(IProductSet).getByName('thunderbird')
    test.globs['collection'] = thunderbird
    login('foo.bar@canonical.com')
    test.globs['newFAQ'] = thunderbird.newFAQ
    login(ANONYMOUS)


def distributionSetUp(test):
    """Test environment for distribution."""
    setUp(test)
    kubuntu = getUtility(IDistributionSet).getByName('kubuntu')
    test.globs['collection'] = kubuntu
    login('foo.bar@canonical.com')
    test.globs['newFAQ'] = kubuntu.newFAQ
    login(ANONYMOUS)


def projectSetUp(test):
    """Test environment for project."""
    setUp(test)
    gnome_project = getUtility(IProjectSet).getByName('gnome')
    products_queue = list(gnome_project.products)

    def newFAQ(owner, title, content, keywords=None, date_created=None):
        """Create a new FAQ on each project's product in turn."""
        product = products_queue.pop(0)
        products_queue.append(product)
        return product.newFAQ(
            owner, title, content, keywords=keywords,
            date_created=date_created)

    test.globs['collection'] = gnome_project
    test.globs['newFAQ'] = newFAQ


def test_suite():
    suite = unittest.TestSuite()

    targets = [('product', productSetUp),
               ('distribution', distributionSetUp),
               ('project', projectSetUp),
               ]

    for name, setUpMethod in targets:
        test = LayeredDocFileSuite('faqcollection.txt',
                    setUp=setUpMethod, tearDown=tearDown,
                    layer=DatabaseFunctionalLayer)
        suite.addTest(test)

    return suite

