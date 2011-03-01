# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests that various objects implement specification-related interfaces."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from lp.blueprints.interfaces.specificationtarget import (
    IHasSpecifications, ISpecificationTarget)
from lp.testing import TestCaseWithFactory


class ImplementsIHasSpecificationsTests(TestCaseWithFactory):
    """Test that various objects implement IHasSpecifications."""
    layer = DatabaseFunctionalLayer

    def test_product_implements_IHasSpecifications(self):
        product = self.factory.makeProduct()
        self.assertProvides(product, IHasSpecifications)

    def test_distribution_implements_IHasSpecifications(self):
        product = self.factory.makeProduct()
        self.assertProvides(product, IHasSpecifications)

    def test_projectgroup_implements_IHasSpecifications(self):
        projectgroup = self.factory.makeProject()
        self.assertProvides(projectgroup, IHasSpecifications)

    def test_person_implements_IHasSpecifications(self):
        person = self.factory.makePerson()
        self.assertProvides(person, IHasSpecifications)

    def test_productseries_implements_IHasSpecifications(self):
        productseries = self.factory.makeProductSeries()
        self.assertProvides(productseries, IHasSpecifications)

    def test_distroseries_implements_IHasSpecifications(self):
        distroseries = self.factory.makeDistroSeries()
        self.assertProvides(distroseries, IHasSpecifications)

    def test_sprint_implements_IHasSpecifications(self):
        sprint = self.factory.makeSprint()
        self.assertProvides(sprint, IHasSpecifications)


class ImplementsISpecificationTargetTests(TestCaseWithFactory):
    """Test that various objects implement ISpecificationTarget."""
    layer = DatabaseFunctionalLayer

    def test_product_implements_ISpecificationTarget(self):
        product = self.factory.makeProduct()
        self.assertProvides(product, ISpecificationTarget)

    def test_distribution_implements_ISpecificationTarget(self):
        product = self.factory.makeProduct()
        self.assertProvides(product, ISpecificationTarget)

    def test_productseries_implements_ISpecificationTarget(self):
        productseries = self.factory.makeProductSeries()
        self.assertProvides(productseries, ISpecificationTarget)

    def test_distroseries_implements_ISpecificationTarget(self):
        distroseries = self.factory.makeDistroSeries()
        self.assertProvides(distroseries, ISpecificationTarget)
