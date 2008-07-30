# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test methods of the Product content class."""

import datetime
import pytz
import unittest
import transaction

from canonical.database.sqlbase import flush_database_updates
from canonical.testing import LaunchpadFunctionalLayer

from canonical.launchpad.interfaces.product import License
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.productlicense import ProductLicense
from canonical.launchpad.database.commercialsubscription import (
    CommercialSubscription)

class ProductAttributeCacheTestCase(unittest.TestCase):
    """Cached attributes must be cleared at the end of a transaction."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        self.product = Product.selectOneBy(name='tomcat')

    def testLicensesCache(self):
        """License cache should be cleared automatically."""
        self.assertEqual(self.product.licenses,
                         (License.ACADEMIC, License.AFFERO))
        ProductLicense(product=self.product, license=License.PYTHON)
        flush_database_updates()
        # Cache doesn't see new value.
        self.assertEqual(self.product.licenses,
                         (License.ACADEMIC, License.AFFERO))
        self.product.licenses = (License.PERL, License.PHP)
        self.assertEqual(self.product.licenses,
                         (License.PERL, License.PHP))
        # Cache is cleared and it sees database changes that occur
        # before the cache is populated.
        transaction.abort()
        ProductLicense(product=self.product, license=License.MIT)
        flush_database_updates()
        self.assertEqual(self.product.licenses,
                         (License.ACADEMIC, License.AFFERO, License.MIT))

    def testCommercialSubscriptionCache(self):
        """commercial_subscription cache should not traverse transactions."""
        self.assertEqual(self.product.commercial_subscription, None)
        now = datetime.datetime.now(pytz.UTC)
        CommercialSubscription(
            product=self.product,
            date_starts=now,
            date_expires=now,
            registrant=self.product.owner,
            purchaser=self.product.owner,
            sales_system_id='foo',
            whiteboard='bar')
        # Cache does not see the change to the database.
        flush_database_updates()
        self.assertEqual(self.product.commercial_subscription, None)
        self.product.redeemSubscriptionVoucher(
            'hello', self.product.owner, self.product.owner, 1)
        self.assertEqual(self.product.commercial_subscription.sales_system_id,
                         'hello')
        transaction.abort()
        # Cache is cleared.
        self.assertEqual(self.product.commercial_subscription, None)

        transaction.abort()
        CommercialSubscription(
            product=self.product,
            date_starts=now,
            date_expires=now,
            registrant=self.product.owner,
            purchaser=self.product.owner,
            sales_system_id='new',
            whiteboard='')
        flush_database_updates()
        # Cache is cleared and it sees database changes that occur
        # before the cache is populated.
        self.assertEqual(self.product.commercial_subscription.sales_system_id,
                         'new')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
