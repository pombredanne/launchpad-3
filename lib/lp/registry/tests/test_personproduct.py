# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Person/Product non-database class."""

__metaclass__ = type

from lp.registry.model.personproduct import PersonProduct
from lp.services.webapp.publisher import canonical_url
from lp.services.webapp.url import urlappend
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestPersonProductCanonicalUrl(TestCaseWithFactory):
    """Tests for the canonical url of `IPersonProduct`s."""

    layer = DatabaseFunctionalLayer

    def test_canonical_url(self):
        # The canonical_url of a person product is ~person/product.
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        pp = PersonProduct(person, product)
        self.assertEqual(
            urlappend(canonical_url(person),
                      product.name),
            canonical_url(pp))
