# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for branch contexts."""

__metaclass__ = type

import unittest

from canonical.launchpad.database.branchtarget import (
    PackageBranchTarget, PersonBranchTarget, ProductBranchTarget)
from canonical.launchpad.interfaces.branchtarget import IBranchTarget
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class TestPackageBranchTarget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a package context is distro/series/sourcepackage
        sourcepackage = self.factory.makeSourcePackage()
        context = PackageBranchTarget(sourcepackage)
        self.assertEqual(sourcepackage.path, context.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        sourcepackage = self.factory.makeSourcePackage()
        context = PackageBranchTarget(sourcepackage)
        namespace = context.getNamespace(person)
        self.assertEqual(person, namespace.owner)
        self.assertEqual(sourcepackage, namespace.sourcepackage)

    def test_adapter(self):
        package = self.factory.makeSourcePackage()
        target = IBranchTarget(package)
        self.assertIsInstance(target, PackageBranchTarget)


class TestPersonBranchTarget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a junk context is '+junk'.
        context = PersonBranchTarget(self.factory.makePerson())
        self.assertEqual('+junk', context.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        context = PersonBranchTarget(self.factory.makePerson())
        namespace = context.getNamespace(person)
        self.assertEqual(namespace.owner, person)
        self.assertRaises(AttributeError, lambda: namespace.product)
        self.assertRaises(AttributeError, lambda: namespace.sourcepackage)

    def test_adapter(self):
        person = self.factory.makePerson()
        target = IBranchTarget(person)
        self.assertIsInstance(target, PersonBranchTarget)


class TestProductBranchTarget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        product = self.factory.makeProduct()
        context = ProductBranchTarget(product)
        self.assertEqual(product.name, context.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        product = self.factory.makeProduct()
        person = self.factory.makePerson()
        context = ProductBranchTarget(product)
        namespace = context.getNamespace(person)
        self.assertEqual(namespace.product, product)
        self.assertEqual(namespace.owner, person)

    def test_adapter(self):
        product = self.factory.makeProduct()
        target = IBranchTarget(product)
        self.assertIsInstance(target, ProductBranchTarget)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
