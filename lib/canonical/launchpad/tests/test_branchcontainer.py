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


class TestPersonContainer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a junk context is '+junk'.
        context = PersonContainer(self.factory.makePerson())
        self.assertEqual('+junk', context.name)


class TestProductContainer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        product = self.factory.makeProduct()
        context = ProductContainer(product)
        self.assertEqual(product.name, context.name)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
