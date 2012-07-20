# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test IStructuralSubscription adapters"""

__metaclass__ = type

from lp.bugs.adapters.structuralsubscription import (
    subscription_to_product,
    )
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class StructuralSubscriptionTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_subscription_to_product_with_product(self):
        product = self.factory.makeProduct()
        subscriber = product.owner
        login_person(subscriber)
        subscription = product.addBugSubscription(subscriber, subscriber)
        self.assertEqual(product, subscription_to_product(subscription))
        #this.assertEqual(product, IProduct(bug_subscription_filter))
