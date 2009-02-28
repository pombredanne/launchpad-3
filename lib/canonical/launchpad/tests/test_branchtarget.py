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


class BaseBranchTargetTests:

    def test_provides_IPrimaryContext(self):
        self.assertProvides(self.target, IPrimaryContext)

    def test_context(self):
        # IBranchTarget.context is the original object.
        self.assertEqual(self.original, self.target.context)


class TestPackageBranchTarget(TestCaseWithFactory, BaseBranchTargetTests):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.original = self.factory.makeSourcePackage()
        self.target = PackageBranchTarget(self.original)

    def test_name(self):
        # The name of a package context is distro/series/sourcepackage
        self.assertEqual(self.original.path, self.target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        namespace = self.target.getNamespace(person)
        self.assertEqual(person, namespace.owner)
        self.assertEqual(self.original, namespace.sourcepackage)

    def test_adapter(self):
        target = IBranchTarget(self.original)
        self.assertIsInstance(self.target, PackageBranchTarget)


class TestPersonBranchTarget(TestCaseWithFactory, BaseBranchTargetTests):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.original = self.factory.makePerson()
        self.target = PersonBranchTarget(self.original)

    def test_name(self):
        # The name of a junk context is '+junk'.
        self.assertEqual('+junk', self.target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        namespace = self.target.getNamespace(self.original)
        self.assertEqual(namespace.owner, self.original)
        self.assertRaises(AttributeError, lambda: namespace.product)
        self.assertRaises(AttributeError, lambda: namespace.sourcepackage)

    def test_adapter(self):
        target = IBranchTarget(self.original)
        self.assertIsInstance(target, PersonBranchTarget)


class TestProductBranchTarget(TestCaseWithFactory, BaseBranchTargetTests):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.original = self.factory.makeProduct()
        self.target = ProductBranchTarget(self.original)

    def test_name(self):
        self.assertEqual(self.original.name, self.target.name)

    def test_getNamespace(self):
        """Get namespace produces the correct namespace."""
        person = self.factory.makePerson()
        namespace = self.target.getNamespace(person)
        self.assertEqual(namespace.product, self.original)
        self.assertEqual(namespace.owner, person)

    def test_adapter(self):
        target = IBranchTarget(self.original)
        self.assertIsInstance(target, ProductBranchTarget)


class TestPrimaryContext(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_package_branch(self):
        branch = self.factory.makePackageBranch()
        self.assertEqual(branch.target, IPrimaryContext(branch))

    def test_personal_branch(self):
        branch = self.factory.makePersonalBranch()
        self.assertEqual(branch.target, IPrimaryContext(branch))

    def test_product_branch(self):
        branch = self.factory.makeProductBranch()
        self.assertEqual(branch.target, IPrimaryContext(branch))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
