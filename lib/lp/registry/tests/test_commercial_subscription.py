# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the commercialsubscriptiojn module."""

__metaclass__ = type

from datetime import timedelta

from zope.security.proxy import removeSecurityProxy

from lp.registry.errors import CannotDeleteCommercialSubscription
from lp.registry.interfaces.product import License
from lp.services.database.lpstorm import IStore
from lp.services.propertycache import clear_property_cache
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class CommecialSubscriptionTestCase(TestCaseWithFactory):
    """Test CommercialSubscription."""
    layer = DatabaseFunctionalLayer

    def test_delete_raises_error_when_active(self):
        product = self.factory.makeProduct(
            licenses=[License.OTHER_PROPRIETARY])
        cs = product.commercial_subscription
        self.assertIs(True, cs.is_active)
        self.assertRaises(
            CannotDeleteCommercialSubscription, cs.delete)
