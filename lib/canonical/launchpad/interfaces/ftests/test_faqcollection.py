# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the faqcollection.txt interface test

This module will run the interface test against Product, Distribution,
and a Project.
"""

__metaclass__ = type

__all__ = []

import unittest

from zope.component import getUtility

from canonical.functional import FunctionalDocFileSuite
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.ftests import login, ANONYMOUS
from canonical.launchpad.interfaces import (
    IDistributionSet, IProductSet, IProjectSet)
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)


def productSetUp(test):
    """Test environment for product."""
    setUp(test)
    test.globs['collection'] = getUtility(IProductSet).getByName('thunderbird')
    login('foo.bar@canonical.com')
    test.globs['newFAQ'] = test.globs['collection'].newFAQ
    login(ANONYMOUS)


def distributionSetUp(test):
    """Test environment for distribution."""
    setUp(test)
    test.globs['collection'] = getUtility(IDistributionSet).getByName('kubuntu')
    login('foo.bar@canonical.com')
    test.globs['newFAQ'] = test.globs['collection'].newFAQ
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
        test = FunctionalDocFileSuite('faqcollection.txt',
                    setUp=setUpMethod, tearDown=tearDown,
                    optionflags=default_optionflags, package=__name__,
                    layer=LaunchpadFunctionalLayer)
        suite.addTest(test)

    return suite

