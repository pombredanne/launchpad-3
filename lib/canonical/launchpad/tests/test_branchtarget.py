# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for branch contexts."""

__metaclass__ = type

import unittest

from canonical.launchpad.database.branchtarget import (
    PackageBranchTarget, PersonBranchTarget, ProductBranchTarget)
from canonical.launchpad.interfaces.branchtarget import IBranchTarget
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.interfaces import IPrimaryContext
from canonical.testing import DatabaseFunctionalLayer


class TestPackageBranchTarget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a package context is distro/series/sourcepackage
        sourcepackage = self.factory.makeSourcePackage()
        target = PackageBranchTarget(sourcepackage)
        self.assertEqual(sourcepackage.path, target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        sourcepackage = self.factory.makeSourcePackage()
        target = PackageBranchTarget(sourcepackage)
        namespace = target.getNamespace(person)
        self.assertEqual(person, namespace.owner)
        self.assertEqual(sourcepackage, namespace.sourcepackage)

    def test_adapter(self):
        package = self.factory.makeSourcePackage()
        target = IBranchTarget(package)
        self.assertIsInstance(target, PackageBranchTarget)

    def test_context(self):
        # IBranchTarget.context is the original object.
        package = self.factory.makeSourcePackage()
        target = PackageBranchTarget(package)
        self.assertEqual(package, target.context)


class TestPersonBranchTarget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a junk context is '+junk'.
        target = PersonBranchTarget(self.factory.makePerson())
        self.assertEqual('+junk', target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        target = PersonBranchTarget(self.factory.makePerson())
        namespace = target.getNamespace(person)
        self.assertEqual(namespace.owner, person)
        self.assertRaises(AttributeError, lambda: namespace.product)
        self.assertRaises(AttributeError, lambda: namespace.sourcepackage)

    def test_adapter(self):
        person = self.factory.makePerson()
        target = IBranchTarget(person)
        self.assertIsInstance(target, PersonBranchTarget)

    def test_context(self):
        # IBranchTarget.context is the original object.
        person = self.factory.makePerson()
        target = PersonBranchTarget(person)
        self.assertEqual(person, target.context)


class TestProductBranchTarget(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        product = self.factory.makeProduct()
        target = ProductBranchTarget(product)
        self.assertEqual(product.name, target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        product = self.factory.makeProduct()
        person = self.factory.makePerson()
        target = ProductBranchTarget(product)
        namespace = target.getNamespace(person)
        self.assertEqual(namespace.product, product)
        self.assertEqual(namespace.owner, person)

    def test_adapter(self):
        product = self.factory.makeProduct()
        target = IBranchTarget(product)
        self.assertIsInstance(target, ProductBranchTarget)

    def test_context(self):
        # IBranchTarget.context is the original object.
        product = self.factory.makeProduct()
        target = ProductBranchTarget(product)
        self.assertEqual(product, target.context)


class TestPrimaryContext(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_package_branch(self):
        branch = self.factory.makePackageBranch()
        self.assertEqual(
            branch.target.context, IPrimaryContext(branch).context)

    def test_personal_branch(self):
        branch = self.factory.makePersonalBranch()
        self.assertEqual(
            branch.target.context, IPrimaryContext(branch).context)

    def test_product_branch(self):
        branch = self.factory.makeProductBranch()
        self.assertEqual(
            branch.target.context, IPrimaryContext(branch).context)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
