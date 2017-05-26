# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the Person/Product non-database class."""

__metaclass__ = type

from lp.app.enums import InformationType
from lp.app.interfaces.informationtype import IInformationType
from lp.app.interfaces.launchpad import IPrivacy
from lp.registry.enums import PersonVisibility
from lp.registry.model.personproduct import PersonProduct
from lp.services.webapp.interfaces import IBreadcrumb
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestPersonProduct(TestCaseWithFactory):
    """Tests for `IPersonProduct`s."""

    layer = DatabaseFunctionalLayer

    def _makePersonProduct(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        return PersonProduct(person, product)

    def test_canonical_url(self):
        # The canonical_url of a person product is ~person/product.
        pp = self._makePersonProduct()
        expected = 'http://launchpad.dev/~%s/%s' % (
            pp.person.name, pp.product.name)
        self.assertEqual(expected, canonical_url(pp))

    def test_breadcrumb(self):
        # Person products give the product as their breadcrumb url.
        pp = self._makePersonProduct()
        breadcrumb = IBreadcrumb(pp, None)
        self.assertEqual(canonical_url(pp.product), breadcrumb.url)

    def test_implements_IInformationType(self):
        pp = self._makePersonProduct()
        verifyObject(IInformationType, pp)

    def test_implements_IPrivacy(self):
        pp = self._makePersonProduct()
        verifyObject(IPrivacy, pp)

    def test_private_person(self):
        # A person product is private if its person (really team) is.
        team = self.factory.makeTeam(visibility=PersonVisibility.PRIVATE)
        product = self.factory.makeProduct()
        pp = PersonProduct(team, product)
        self.assertTrue(pp.private)
        self.assertEqual(InformationType.PUBLIC, pp.information_type)

    def test_private_product(self):
        # A person product is private if its product is.
        person = self.factory.makePerson()
        product = self.factory.makeProduct(
            information_type=InformationType.PROPRIETARY)
        pp = PersonProduct(person, product)
        self.assertTrue(pp.private)
        self.assertEqual(InformationType.PROPRIETARY, pp.information_type)

    def test_public(self):
        # A person product is public if both its person and product are.
        pp = self._makePersonProduct()
        self.assertFalse(pp.private)
        self.assertEqual(InformationType.PUBLIC, pp.information_type)
