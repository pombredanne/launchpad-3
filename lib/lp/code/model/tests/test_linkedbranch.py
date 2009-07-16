# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for linked branch implementations."""

__metaclass__ = type


import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.linkedbranch import (
    CannotHaveLinkedBranch, get_linked_branch, ICanHasLinkedBranch)
from lp.soyuz.interfaces.publishing import PackagePublishingPocket
from lp.testing import run_with_login, TestCaseWithFactory


class TestProductSeriesLinkedBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_branch(self):
        # The linked branch of a product series is its branch attribute.
        product_series = self.factory.makeProductSeries()
        product_series.branch = self.factory.makeProductBranch(
            product=product_series.product)
        self.assertEqual(
            product_series.branch, ICanHasLinkedBranch(product_series).branch)

    def test_setBranch(self):
        # setBranch sets the linked branch of the product series.
        product_series = self.factory.makeProductSeries()
        branch = self.factory.makeProductBranch(
            product=product_series.product)
        ICanHasLinkedBranch(product_series).setBranch(branch)
        self.assertEqual(branch, product_series.branch)


class TestProductLinkedBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_branch(self):
        # The linked branch of a product is the linked branch of its
        # development focus product series.
        branch = self.factory.makeProductBranch()
        product = branch.product
        removeSecurityProxy(product).development_focus.branch = branch
        self.assertEqual(branch, ICanHasLinkedBranch(product).branch)

    def test_setBranch(self):
        # setBranch sets the linked branch of the development focus product
        # series.
        branch = self.factory.makeProductBranch()
        product = removeSecurityProxy(branch.product)
        ICanHasLinkedBranch(product).setBranch(branch)
        self.assertEqual(branch, product.development_focus.branch)


class TestSuiteSourcePackageLinkedBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_branch(self):
        # The linked branch of a suite source package is the official branch
        # for the pocket of that source package.
        branch = self.factory.makeAnyBranch()
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        registrant = ubuntu_branches.teamowner
        run_with_login(
            ubuntu_branches.teamowner,
            sourcepackage.setBranch, pocket, branch, registrant)
        suite_sourcepackage = sourcepackage.getSuiteSourcePackage(pocket)
        self.assertEqual(
            branch, ICanHasLinkedBranch(suite_sourcepackage).branch)

    def test_setBranch(self):
        # setBranch sets the official branch for the appropriate pocket of the
        # source package.
        branch = self.factory.makeAnyBranch()
        sourcepackage = self.factory.makeSourcePackage()
        pocket = PackagePublishingPocket.RELEASE
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        registrant = ubuntu_branches.teamowner
        suite_sourcepackage = sourcepackage.getSuiteSourcePackage(pocket)
        run_with_login(
            registrant,
            ICanHasLinkedBranch(suite_sourcepackage).setBranch,
            branch, registrant)
        self.assertEqual(branch, sourcepackage.getBranch(pocket))


class TestDistributionSourcePackageLinkedBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_branch(self):
        # The linked branch of a distribution source package is the official
        # branch for the release pocket of the development focus series for
        # that package. Phew.
        branch = self.factory.makeAnyBranch()
        sourcepackage = self.factory.makeSourcePackage()
        dev_sourcepackage = sourcepackage.development_version
        pocket = PackagePublishingPocket.RELEASE

        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        registrant = ubuntu_branches.teamowner
        run_with_login(
            ubuntu_branches.teamowner,
            dev_sourcepackage.setBranch, pocket, branch, registrant)

        distribution_sourcepackage = sourcepackage.distribution_sourcepackage
        self.assertEqual(
            branch, ICanHasLinkedBranch(distribution_sourcepackage).branch)

    def test_setBranch(self):
        branch = self.factory.makeAnyBranch()
        sourcepackage = self.factory.makeSourcePackage()
        distribution_sourcepackage = sourcepackage.distribution_sourcepackage

        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        registrant = ubuntu_branches.teamowner
        run_with_login(
            registrant,
            ICanHasLinkedBranch(distribution_sourcepackage).setBranch,
            branch, registrant)

        dev_sourcepackage = sourcepackage.development_version
        pocket = PackagePublishingPocket.RELEASE
        self.assertEqual(branch, dev_sourcepackage.getBranch(pocket))


class TestProjectLinkedBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_cannot_have_linked_branch(self):
        # Projects cannot have linked branches.
        project = self.factory.makeProject()
        self.assertRaises(
            CannotHaveLinkedBranch, get_linked_branch, project)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
