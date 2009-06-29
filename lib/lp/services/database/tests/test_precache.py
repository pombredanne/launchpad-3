# Copyright 2009 Canonical Ltd.  All rights reserved.

"""precache module tests."""

__metaclass__ = type
__all__ = []

import unittest

from storm.expr import And, Join, LeftJoin

from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.interfaces import IMasterStore
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.services.database.precache import precache


class PrecacheTestCase(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.store = IMasterStore(Product)

        # All products
        self.standard_result = self.store.find(Product).order_by(Product.name)

        # All products, with owner and preferred email address precached.
        # Note that because some Product owners have multiple email
        # addresses, this query returns more results. precache needs
        # to hide this from callsites.
        self.unwrapped_result = self.store.using(
                Product,
                Join(Person, Product.ownerID == Person.id),
                LeftJoin(EmailAddress, And(
                    Person.id == EmailAddress.personID,
                    EmailAddress.status == EmailAddressStatus.PREFERRED))
            ).find((Product, Person, EmailAddress)).order_by(Product.name)
        self.precache_result = precache(self.unwrapped_result)

    def test_count(self):
        self.failUnlessEqual(
            self.standard_result.count(),
            self.precache_result.count())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
