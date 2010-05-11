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
        self.product = self.factory.makeProduct(
            name='ball', owner=self.registrant)
        self.view = create_view(self.product, '+edit')
        self.view.product = self.product
        login_person(self.registrant)

    def test_ProductLicenseMixin_instance(self):
        self.assertTrue(isinstance(self.view, ProductLicenseMixin))

    def test_notifyCommercialMailingList_known_license(self):
        # A known license does not generate an email.
        self.product.licenses = [License.GNU_GPL_V2]
        self.view.notifyCommercialMailingList()
        self.assertEqual(0, len(pop_notifications()))

    def test_notifyCommercialMailingList_other_dont_know(self):
        # An Other/I don't know license sends one email.
        self.product.licenses = [License.DONT_KNOW]
        self.view.notifyCommercialMailingList()
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        user_email = notifications.pop()
        self.assertEqual(
            "License information for ball in Launchpad",
            user_email['Subject'])
        self.assertEqual(
            'Registrant <registrant@launchpad.dev>',
            user_email['To'])
        self.assertEqual(
            'Commercial <commercial@launchpad.net>',
            user_email['Reply-To'])

    def test_notifyCommercialMailingList_other_open_source(self):
        # An Other/Open Source license sends two emails.
        self.product.licenses = [License.OTHER_OPEN_SOURCE]
        self.product.license_info = 'http://www,boost.org/'
        self.view.notifyCommercialMailingList()
        notifications = pop_notifications()
        self.assertEqual(2, len(notifications))
        user_email = notifications.pop()
        self.assertEqual(
            "License information for ball in Launchpad",
            user_email['Subject'])
        self.assertEqual(
            'Registrant <registrant@launchpad.dev>',
            user_email['To'])
        self.assertEqual(
            'Commercial <commercial@launchpad.net>',
            user_email['Reply-To'])
        commercial_email = notifications.pop()
        self.assertEqual(
            "Project License Submitted for ball by registrant",
            commercial_email['Subject'])
        self.assertEqual(
            'Commercial <commercial@launchpad.net>',
            commercial_email['To'])

    def test_notifyCommercialMailingList_other_proprietary(self):
        # An Other/Proprietary license sends two emails.
        self.product.licenses = [License.OTHER_PROPRIETARY]
        self.product.license_info = 'All mine'
        self.view.notifyCommercialMailingList()
        notifications = pop_notifications()
        self.assertEqual(2, len(notifications))
        user_email = notifications.pop()
        self.assertEqual(
            "License information for ball in Launchpad",
            user_email['Subject'])
        self.assertEqual(
            'Registrant <registrant@launchpad.dev>',
            user_email['To'])
        self.assertEqual(
            'Commercial <commercial@launchpad.net>',
            user_email['Reply-To'])
        commercial_email = notifications.pop()
        self.assertEqual(
            "Project License Submitted for ball by registrant",
            commercial_email['Subject'])
        self.assertEqual(
            'Commercial <commercial@launchpad.net>',
            commercial_email['To'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
