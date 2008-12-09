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
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        context = PackageContainer(distroseries, sourcepackagename)
        self.assertEqual(
            '%s/%s/%s' % (
                distroseries.distribution.name,
                distroseries.name,
                sourcepackagename.name), context.name)

    def test_getBranches_empty(self):
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        context = PackageContainer(distroseries, sourcepackagename)
        self.assertEqual([], list(context.getBranches()))

    def test_getBranches_some(self):
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        context = PackageContainer(distroseries, sourcepackagename)
        branch = self.factory.makeBranch(
            distroseries=distroseries, sourcepackagename=sourcepackagename)
        self.assertEqual([branch], list(context.getBranches()))


class TestPersonContainer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a junk context is '+junk'.
        context = PersonContainer(self.factory.makePerson())
        self.assertEqual('+junk', context.name)

    def test_getBranches_empty(self):
        person = self.factory.makePerson()
        context = PersonContainer(person)
        self.assertEqual([], list(context.getBranches()))

    def test_getBranches_some(self):
        person = self.factory.makePerson()
        context = PersonContainer(person)
        branch = self.factory.makeBranch(owner=person, product=None)
        self.assertEqual([branch], list(context.getBranches()))


class TestProductContainer(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        product = self.factory.makeProduct()
        context = ProductContainer(product)
        self.assertEqual(product.name, context.name)

    def test_getBranches_empty(self):
        product = self.factory.makeProduct()
        context = ProductContainer(product)
        self.assertEqual([], list(context.getBranches()))

    def test_getBranches_some(self):
        product = self.factory.makeProduct()
        context = ProductContainer(product)
        branch = self.factory.makeBranch(product=product)
        self.assertEqual([branch], list(context.getBranches()))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

