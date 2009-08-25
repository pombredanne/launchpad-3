# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for structural subscription traversal."""

import unittest

from lazr.restful.testing.webservice import FakeRequest
from zope.publisher.interfaces import NotFound

from canonical.launchpad.webapp.servers import StepsToGo
from canonical.launchpad.webapp.publisher import canonical_url
from lp.registry.browser.product import ProductNavigation
from lp.registry.browser.productseries import ProductSeriesNavigation
from lp.registry.browser.milestone import MilestoneNavigation
from lp.registry.browser.project import ProjectNavigation
from lp.registry.browser.distribution import DistributionNavigation
from lp.registry.browser.distroseries import DistroSeriesNavigation
from lp.registry.browser.distributionsourcepackage import (
    DistributionSourcePackageNavigation)

from canonical.launchpad.ftests import login, logout
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class FakeLaunchpadRequest(FakeRequest):
    @property
    def stepstogo(self):
        """See `IBasicLaunchpadRequest`."""
        return StepsToGo(self)


class TestBaseStructuralSubscriptionTraversal(TestCaseWithFactory):
    """Verify that we can reach a target's structural subscriptions."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBaseStructuralSubscriptionTraversal, self).setUp()
        login('foo.bar@canonical.com')
        self.eric = self.factory.makePerson(name='eric')
        self.michael = self.factory.makePerson(name='michael')

        self.setUpTarget()
        self.target.addBugSubscription(self.eric, self.eric)

    def setUpTarget(self):
        self.target = self.factory.makeProduct(name='fooix')
        self.navigation = ProductNavigation

    def test_structural_subscription_traversal(self):
        request = FakeLaunchpadRequest([], ['eric'])
        self.assertEqual(
            self.target.getSubscription(self.eric),
            self.navigation(self.target, request).publishTraverse(
                request, '+subscription'))

    def test_missing_structural_subscription_traversal(self):
        request = FakeLaunchpadRequest([], ['michael'])
        self.assertRaises(
            NotFound,
            self.navigation(self.target, request).publishTraverse,
            request, '+subscription')

    def test_missing_person_structural_subscription_traversal(self):
        request = FakeLaunchpadRequest([], ['doesnotexist'])
        self.assertRaises(
            NotFound,
            self.navigation(self.target, request).publishTraverse,
            request, '+subscription')

    def test_structural_subscription_canonical_url(self):
        request = FakeLaunchpadRequest([], ['eric'])
        self.assertEqual(
            canonical_url(self.target.getSubscription(self.eric)),
            canonical_url(self.target) + '/+subscription/eric')

    def tearDown(self):
        logout()
        super(TestBaseStructuralSubscriptionTraversal, self).tearDown()


class TestProductSeriesStructuralSubscriptionTraversal(
    TestBaseStructuralSubscriptionTraversal):
    def setUpTarget(self):
        self.target = self.factory.makeProduct(name='fooix').newSeries(
            self.eric, '0.1', '0.1')
        self.navigation = ProductSeriesNavigation


class TestMilestoneStructuralSubscriptionTraversal(
    TestBaseStructuralSubscriptionTraversal):
    def setUpTarget(self):
        self.target = self.factory.makeProduct(name='fooix').newSeries(
            self.eric, '0.1', '0.1').newMilestone('0.1.0')
        self.navigation = MilestoneNavigation


class TestProjectStructuralSubscriptionTraversal(
    TestBaseStructuralSubscriptionTraversal):
    def setUpTarget(self):
        self.target = self.factory.makeProject(name='fooix-project')
        self.navigation = ProjectNavigation


class TestDistributionStructuralSubscriptionTraversal(
    TestBaseStructuralSubscriptionTraversal):
    def setUpTarget(self):
        self.target = self.factory.makeDistribution(name='debuntu')
        self.navigation = DistributionNavigation


class TestDistroSeriesStructuralSubscriptionTraversal(
    TestBaseStructuralSubscriptionTraversal):
    def setUpTarget(self):
        self.target = self.factory.makeDistribution(name='debuntu').newSeries(
            '5.0', '5.0', '5.0', '5.0', '5.0', '5.0', None, self.eric)
        self.navigation = DistroSeriesNavigation


class TestDistributionSourcePackagetructuralSubscriptionTraversal(
    TestBaseStructuralSubscriptionTraversal):
    def setUpTarget(self):
        debuntu = self.factory.makeDistribution(name='debuntu')
        fooix = self.factory.makeSourcePackageName('fooix')
        self.target = debuntu.getSourcePackage(fooix)
        self.navigation = DistributionSourcePackageNavigation


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
