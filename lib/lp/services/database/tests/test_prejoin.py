# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""prejoin module tests."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.launchpad.interfaces import IMasterStore
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.services.database.prejoin import (
    prejoin,
    PrejoinResultSet,
    )
from lp.testing import TestCase


class PrejoinTestCase(TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(PrejoinTestCase, self).setUp()
        self.store = IMasterStore(Product)

        # All products
        self.standard_result = self.store.find(Product).order_by(Product.name)

        # All products, with owner and preferred email address prejoined.
        # Note that because some Product owners have multiple email
        # addresses, this query returns more results. prejoin needs
        # to hide this from callsites.
        self.unwrapped_result = self.store.find(
            (Product, Person),
            Product._ownerID == Person.id).order_by(Product.name)
        self.prejoin_result = prejoin(self.unwrapped_result)

    def verify(self, prejoined, normal):
        # Ensure our prejoined result really is a PrejoinResultSet.
        # One of our methods might not be sticky, and we have ended up
        # with a normal Storm ResultSet.
        self.assertTrue(
            isinstance(prejoined, PrejoinResultSet),
            "Expected a PrejoinResultSet, got %s" % repr(prejoined))

        # Confirm the two result sets return identical results.
        self.assertEqual(list(normal), list(prejoined))

    def test_count(self):
        self.assertEqual(
            self.standard_result.count(),
            self.prejoin_result.count())

    def test_copy(self):
        copy = self.prejoin_result.copy()
        self.verify(copy, self.standard_result)

    def test_config(self):
        self.prejoin_result.config(offset=3, limit=2)
        self.standard_result.config(offset=3, limit=2)
        self.verify(self.prejoin_result, self.standard_result)

    def test_config_returnvalue(self):
        prejoin_rv = self.prejoin_result.config(offset=3, limit=2)
        standard_rv = self.standard_result.config(offset=3, limit=2)
        self.verify(prejoin_rv, standard_rv)

    def test_order_by(self):
        self.verify(
            self.prejoin_result.order_by(Product.id),
            self.standard_result.order_by(Product.id))

    def test_slice(self):
        self.verify(
            self.prejoin_result[4:6],
            self.standard_result[4:6])

    def test_any(self):
        self.assertIn(self.prejoin_result.any(), self.standard_result)

    def test_first(self):
        self.assertEqual(
            self.standard_result.first(), self.prejoin_result.first())

    def test_one(self):
        standard_result = self.store.find(Product, Product.name == 'firefox')
        prejoin_result = prejoin(self.store.find(
            (Product, Person),
            Person.id == Product._ownerID,
            Product.name == 'firefox'))
        self.assertEqual(standard_result.one(), prejoin_result.one())

    def test_one_empty(self):
        # For an empty result (None), one returns None, too.
        name = "none-existent-name"
        prejoin_result = prejoin(self.store.find(
            (Product, Person),
            Person.id == Product._ownerID,
            Product.name == name))
        self.assertIs(None, prejoin_result.one())

    def test_cache_populated(self):
        # Load a row.
        product = self.prejoin_result.first()

        # Destroy our data, without telling Storm. This way we can
        # tell if we are accessing an object from the cache, or if it
        # was retrieved from the database.
        self.store.execute("UPDATE Person SET displayname='foo'")

        self.failIfEqual('foo', product.owner.displayname)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
