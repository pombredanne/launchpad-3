# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getMultiAdapter

from canonical.lazr.testing.menus import make_fake_request
from canonical.launchpad.webapp.publisher import RootObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestExtraVHostBreadcrumbsOnHierarchyView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.product = self.factory.makeProduct()
        self.bug = self.factory.makeBug(product=self.product)
        self.root = RootObject()

    def test_root_on_mainsite(self):
        request = make_fake_request('http://launchpad.dev/', [self.root])
        hierarchy = getMultiAdapter((self.root, request), name='+hierarchy')
        self.assertEquals(hierarchy.items(), [])

    def test_product_on_mainsite(self):
        request = make_fake_request(
            'http://launchpad.dev/%s' % self.product.name,
            [self.root, self.product])
        hierarchy = getMultiAdapter((self.root, request), name='+hierarchy')
        self.assertEquals(hierarchy.items(), [])

    def test_root_on_vhost(self):
        request = make_fake_request('http://bugs.launchpad.dev/', [self.root])
        hierarchy = getMultiAdapter((self.root, request), name='+hierarchy')
        self.assertEquals(hierarchy.items(), [])

    def test_product_on_vhost(self):
        request = make_fake_request(
            'http://bugs.launchpad.dev/%s' % self.product.name,
            [self.root, self.product])
        hierarchy = getMultiAdapter((self.root, request), name='+hierarchy')
        self.assertEquals(hierarchy.items(), [])

    
def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
