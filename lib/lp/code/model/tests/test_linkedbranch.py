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
from lp.registry.interfaces.distroseries import NoSuchDistroSeries
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

    def test_bzr_path(self):
        # The bzr_path of a product series linked branch is
        # product/product_series.
        product_series = self.factory.makeProductSeries()
        bzr_path = '%s/%s' % (
            product_series.product.name, product_series.name)
        self.assertEqual(
            bzr_path, ICanHasLinkedBranch(product_series).bzr_path)


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

    def test_bzr_path(self):
        # The bzr_path of a product linked branch is the product name.
        product = self.factory.makeProduct()
        self.assertEqual(
            product.name, ICanHasLinkedBranch(product).bzr_path)


class TestSuiteSourcePackageLinkedBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_branch(self):
        # The linked branch of a suite source package is the official branch
        # for the pocket of that source package.
        branch = self.factory.makeAnyBranch()
        suite_sourcepackage = self.factory.makeSuiteSourcePackage()
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        registrant = ubuntu_branches.teamowner
        run_with_login(
            registrant,
            suite_sourcepackage.sourcepackage.setBranch,
            suite_sourcepackage.pocket, branch, registrant)
        self.assertEqual(
            branch, ICanHasLinkedBranch(suite_sourcepackage).branch)

    def test_setBranch(self):
        # setBranch sets the official branch for the appropriate pocket of the
        # source package.
        branch = self.factory.makeAnyBranch()
        suite_sourcepackage = self.factory.makeSuiteSourcePackage()
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        registrant = ubuntu_branches.teamowner
        run_with_login(
            registrant,
            ICanHasLinkedBranch(suite_sourcepackage).setBranch,
            branch, registrant)
        self.assertEqual(
            branch,
            suite_sourcepackage.sourcepackage.getBranch(
                suite_sourcepackage.pocket))

    def test_bzr_path(self):
        # The bzr_path of a suite source package linked branch is the path
        # of that suite source package.
        suite_sourcepackage = self.factory.makeSuiteSourcePackage()
        self.assertEqual(
            suite_sourcepackage.path,
            ICanHasLinkedBranch(suite_sourcepackage).bzr_path)


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

    def test_branch_when_no_series(self):
        # Our data model allows distributions that have no series. The linked
        # branch for a package in such a distribution is always None.
        distro_package = self.factory.makeDistributionSourcePackage()
        self.assertIs(None, ICanHasLinkedBranch(distro_package).branch)

    def test_setBranch(self):
        # Setting the linked branch for a distribution source package links
        # the branch to the release pocket of the development focus series for
        # that package.
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

    def test_setBranch_with_no_series(self):
        distribution_sourcepackage = (
            self.factory.makeDistributionSourcePackage())
        linked_branch = ICanHasLinkedBranch(distribution_sourcepackage)
        ubuntu_branches = getUtility(ILaunchpadCelebrities).ubuntu_branches
        registrant = ubuntu_branches.teamowner
        self.assertRaises(
            NoSuchDistroSeries,
            linked_branch.setBranch, self.factory.makeAnyBranch(), registrant)

    def test_bzr_path(self):
        # The bzr_path of a distribution source package linked branch is
        # distro/package.
        distribution_sourcepackage = (
            self.factory.makeDistributionSourcePackage())
        self.assertEqual(
            '%s/%s' % (
                distribution_sourcepackage.distribution.name,
                distribution_sourcepackage.sourcepackagename.name),
            ICanHasLinkedBranch(distribution_sourcepackage).bzr_path)


class TestProjectLinkedBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_cannot_have_linked_branch(self):
        # Projects cannot have linked branches.
        project = self.factory.makeProject()
        self.assertRaises(
            CannotHaveLinkedBranch, get_linked_branch, project)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
