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
from lp.services.database.precache import precache, PrecacheResultSet


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

    def verify(self, precached, normal):
        # Ensure our precached result really is a PrecacheResultSet.
        # One of our methods might not be sticky, and we have ended up
        # with a normal Storm ResultSet.
        self.failUnless(
            isinstance(precached, PrecacheResultSet),
            "Expected a PrecacheResultSet, got %s" % repr(precached))

        # Confirm the two result sets return identical results.
        self.failUnlessEqual(list(precached), list(normal))

    def test_count(self):
        self.failUnlessEqual(
            self.standard_result.count(),
            self.precache_result.count())

    def test_copy(self):
        copy = self.precache_result.copy()
        self.verify(copy, self.standard_result)

    def test_config(self):
        self.precache_result.config(offset=3, limit=2)
        self.standard_result.config(offset=3, limit=2)
        self.verify(self.precache_result, self.standard_result)

    def test_config_returnvalue(self):
        precache_rv = self.precache_result.config(offset=3, limit=2)
        standard_rv = self.standard_result.config(offset=3, limit=2)
        self.verify(precache_rv, standard_rv)

    def test_order_by(self):
        self.verify(
            self.precache_result.order_by(Product.id),
            self.standard_result.order_by(Product.id))

    def test_slice(self):
        self.verify(
            self.precache_result[4:6],
            self.standard_result[4:6])

    def test_any(self):
        self.failUnless(self.precache_result.any() in self.standard_result)

    def test_first(self):
        self.failUnlessEqual(
            self.precache_result.first(), self.standard_result.first())

    def test_one(self):
        standard_result = self.store.find(Person, Person.name == 'name12')
        precache_result = precache(self.store.find(
            (Person,EmailAddress),
            Person.id == EmailAddress.personID,
            Person.name == 'name12',
            EmailAddress.status == EmailAddressStatus.PREFERRED))
        self.failUnlessEqual(standard_result.one(), precache_result.one())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
