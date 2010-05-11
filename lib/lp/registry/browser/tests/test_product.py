# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for product views."""

__metaclass__ = type

import unittest

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import login_person, TestCaseWithFactory
from lp.testing.mail_helpers import pop_notifications
from lp.testing.views import create_view

from lp.registry.interfaces.product import License
from lp.registry.browser.product import ProductLicenseMixin


class TestProductLicenseMixin(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Setup an a view that implements ProductLicenseMixin.
        super(TestProductLicenseMixin, self).setUp()
        self.registrant = self.factory.makePerson(
            name='registrant', email='registrant@launchpad.dev')
        self.product = self.factory.makeProduct(name='ball')
        self.view = create_view(self.product, '+edit')
        self.view.product = self.product
        login_person(self.product.owner)

    def test_ProductLicenseMixin_instance(self):
        self.assertTrue(isinstance(self.view, ProductLicenseMixin))

    def test_notifyCommercialMailingList_known_license(self):
        # A known license does not generate an email.
        self.product.licenses = [License.GNU_GPL_V2]
        self.view.notifyCommercialMailingList()
        self.assertEqual(0, len(pop_notifications()))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
