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


class TestLinkedBranch(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product_series(self):
        # The linked branch of a product series is its branch attribute.
        product_series = self.factory.makeProductSeries()
        product_series.branch = self.factory.makeProductBranch(
            product=product_series.product)
        self.assertEqual(
            product_series.branch, ICanHasLinkedBranch(product_series).branch)

    def test_product(self):
        # The linked branch of a product is the linked branch of its
        # development focus product series.
        branch = self.factory.makeProductBranch()
        product = branch.product
        removeSecurityProxy(product).development_focus.branch = branch
        self.assertEqual(branch, ICanHasLinkedBranch(product).branch)

    def test_suitesourcepackage(self):
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

    def test_project(self):
        project = self.factory.makeProject()
        self.assertRaises(
            CannotHaveLinkedBranch, get_linked_branch, project)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
