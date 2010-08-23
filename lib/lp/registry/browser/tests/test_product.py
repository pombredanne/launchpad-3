# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for product views."""

__metaclass__ = type

import datetime
import unittest

import pytz
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.browser.product import ProductLicenseMixin
from lp.registry.interfaces.product import License
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.mail_helpers import pop_notifications
from lp.testing.views import create_view


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

    def verify_whiteboard(self):
        # Verify that the review whiteboard was updated.
        naked_product = removeSecurityProxy(self.product)
        whiteboard, stamp = naked_product.reviewer_whiteboard.rsplit(' ', 1)
        self.assertEqual(
            'User notified of license policy on', whiteboard)

    def verify_user_email(self, notification):
        # Verify that the user was sent an email about the license change.
        self.assertEqual(
            'License information for ball in Launchpad',
            notification['Subject'])
        self.assertEqual(
            'Registrant <registrant@launchpad.dev>',
            notification['To'])
        self.assertEqual(
            'Commercial <commercial@launchpad.net>',
            notification['Reply-To'])

    def verify_commercial_email(self, notification):
        # Verify that the commercial team was sent an email.
        self.assertEqual(
            'Project License Submitted for ball by registrant',
            notification['Subject'])
        self.assertEqual(
            'Commercial <commercial@launchpad.net>',
            notification['To'])

    def test_ProductLicenseMixin_instance(self):
        # The object under test is an instance of ProductLicenseMixin.
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
        self.verify_whiteboard()
        notifications = pop_notifications()
        self.assertEqual(1, len(notifications))
        self.verify_user_email(notifications.pop())

    def test_notifyCommercialMailingList_other_open_source(self):
        # An Other/Open Source license sends two emails.
        self.product.licenses = [License.OTHER_OPEN_SOURCE]
        self.product.license_info = 'http://www,boost.org/'
        self.view.notifyCommercialMailingList()
        self.verify_whiteboard()
        notifications = pop_notifications()
        self.assertEqual(2, len(notifications))
        self.verify_user_email(notifications.pop())
        self.verify_commercial_email(notifications.pop())

    def test_notifyCommercialMailingList_other_proprietary(self):
        # An Other/Proprietary license sends two emails.
        self.product.licenses = [License.OTHER_PROPRIETARY]
        self.product.license_info = 'All mine'
        self.view.notifyCommercialMailingList()
        self.verify_whiteboard()
        notifications = pop_notifications()
        self.assertEqual(2, len(notifications))
        self.verify_user_email(notifications.pop())
        self.verify_commercial_email(notifications.pop())

    def test__formatDate(self):
        # Verify the date format.
        now = datetime.datetime(2005, 6, 15, 0, 0, 0, 0, pytz.UTC)
        result = self.view._formatDate(now)
        self.assertEqual('2005-06-15', result)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
