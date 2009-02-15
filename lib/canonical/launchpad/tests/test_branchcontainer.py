# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for branch contexts."""

__metaclass__ = type

import unittest

from canonical.launchpad.database.branchcontainer import (
    PackageContainer, PersonContainer, ProductContainer)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class TestPackageContainer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a package context is distro/series/sourcepackage
        sourcepackage = self.factory.makeSourcePackage()
        context = PackageContainer(sourcepackage)
        self.assertEqual(sourcepackage.path, context.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        sourcepackage = self.factory.makeSourcePackage()
        context = PackageContainer(sourcepackage)
        namespace = context.getNamespace(person)
        self.assertEqual(person, namespace.owner)
        self.assertEqual(sourcepackage, namespace.sourcepackage)


class TestPersonContainer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a junk context is '+junk'.
        context = PersonContainer(self.factory.makePerson())
        self.assertEqual('+junk', context.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        context = PersonContainer(self.factory.makePerson())
        namespace = context.getNamespace(person)
        self.assertEqual(namespace.owner, person)
        self.assertRaises(AttributeError, lambda: namespace.product)
        self.assertRaises(AttributeError, lambda: namespace.sourcepackage)


class TestProductContainer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        product = self.factory.makeProduct()
        context = ProductContainer(product)
        self.assertEqual(product.name, context.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        product = self.factory.makeProduct()
        person = self.factory.makePerson()
        context = ProductContainer(product)
        namespace = context.getNamespace(person)
        self.assertEqual(namespace.product, product)
        self.assertEqual(namespace.owner, person)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
