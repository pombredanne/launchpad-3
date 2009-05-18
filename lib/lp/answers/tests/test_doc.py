# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
Run the doctests and pagetests.
"""

import logging
import os
import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import login, ANONYMOUS
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.project import IProjectSet
from canonical.launchpad.testing.pages import PageTestSuite
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import DatabaseFunctionalLayer

from lp.services.testing import build_test_suite


here = os.path.dirname(os.path.realpath(__file__))

def productSetUp(test):
    """Test environment for product."""
    setUp(test)
    thunderbird = getUtility(IProductSet).getByName('thunderbird')
    test.globs['target'] = thunderbird
    test.globs['collection'] = thunderbird
    login('foo.bar@canonical.com')
    test.globs['newFAQ'] = thunderbird.newFAQ
    login(ANONYMOUS)


def distributionSetUp(test):
    """Test environment for distribution."""
    setUp(test)
    kubuntu = getUtility(IDistributionSet).getByName('kubuntu')
    test.globs['target'] = kubuntu
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

def sourcepackageSetUp(test):
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['target'] = ubuntu.currentseries.getSourcePackage('evolution')


def distributionsourcepackageSetUp(test):
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['target'] = ubuntu.getSourcePackage('evolution')


def create_interface_test_suite(test_file, targets):
    """Create a test suite for an interface test using several fixtures."""

    suite = unittest.TestSuite()
    for name, setup_func in targets:
        test = LayeredDocFileSuite(
            os.path.join(os.path.pardir, 'doc', test_file),
                    setUp=setup_func, tearDown=tearDown,
                    layer=DatabaseFunctionalLayer)
        suite.addTest(test)
    return suite


special = {
    'questiontarget.txt': create_interface_test_suite(
        'questiontarget.txt',
        [('product', productSetUp),
         ('distribution', distributionSetUp),
         ('sourcepackage', sourcepackageSetUp),
         ('distributionsourcepackage', distributionsourcepackageSetUp),
         ]),

    'faqtarget.txt': create_interface_test_suite(
        'faqtarget.txt',
        [('product', productSetUp),
         ('distribution', distributionSetUp),
         ]),

    'faqcollection.txt': create_interface_test_suite(
        'faqcollection.txt',
        [('product', productSetUp),
         ('distribution', distributionSetUp),
         ('project', projectSetUp),
         ])
    }


def test_suite():
    return build_test_suite(here, special)

