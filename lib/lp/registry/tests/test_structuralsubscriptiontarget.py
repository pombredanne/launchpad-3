# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running tests against IStructuralsubscriptionTarget
implementations.
"""
__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import (
    ProxyFactory,
    removeSecurityProxy,
    )

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import LaunchpadFunctionalLayer
from lp.bugs.interfaces.bug import CreateBugParams
from lp.bugs.tests.test_bugtarget import bugtarget_filebug
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.registry.interfaces.structuralsubscription import (
    DeleteSubscriptionError,
    IStructuralSubscriptionTarget,
    UserCannotSubscribePerson,
    )
from lp.registry.model.structuralsubscription import StructuralSubscription
from lp.testing import (
    ANONYMOUS,
    login,
    login_person,
    TestCaseWithFactory,
    )
from lp.testing._login import login_celebrity


class StructuralSubscriptionTestBase:

    def setUp(self):
        super(StructuralSubscriptionTestBase, self).setUp()
        self.ordinary_subscriber = self.factory.makePerson()
        self.bug_supervisor_subscriber = self.factory.makePerson()
        self.team_owner = self.factory.makePerson()
        self.team = self.factory.makeTeam(owner=self.team_owner)

    def test_target_implements_structural_subscription_target(self):
        self.assertTrue(verifyObject(IStructuralSubscriptionTarget,
                                     self.target))

    def test_anonymous_cannot_subscribe_anyone(self):
        # only authenticated users can create structural subscriptions
        login(ANONYMOUS)
        self.assertRaises(Unauthorized, getattr, self.target,
                          'addBugSubscription')

    def test_person_structural_subscription_by_other_person(self):
        # a person can not subscribe someone else willy nilly
        login_person(self.ordinary_subscriber)
        self.assertRaises(UserCannotSubscribePerson,
            self.target.addBugSubscription,
            self.team_owner, self.ordinary_subscriber)

    def test_team_structural_subscription_by_non_team_member(self):
        # a person not related to a team cannot subscribe it
        login_person(self.ordinary_subscriber)
        self.assertRaises(UserCannotSubscribePerson,
            self.target.addBugSubscription,
            self.team, self.ordinary_subscriber)

    def test_admin_can_subscribe_anyone(self):
        # a launchpad admin can create a structural subscription for
        # anyone
        admin = login_celebrity('admin')
        self.assertIsInstance(
            self.target.addBugSubscription(self.ordinary_subscriber, admin),
            StructuralSubscription)

    def test_secondary_structural_subscription(self):
        # creating a structural subscription a 2nd time returns the
        # first structural subscription
        login_person(self.bug_supervisor_subscriber)
        subscription1 = self.target.addBugSubscription(
            self.bug_supervisor_subscriber, self.bug_supervisor_subscriber)
        subscription2 = self.target.addBugSubscription(
            self.bug_supervisor_subscriber, self.bug_supervisor_subscriber)
        self.assertIs(subscription1.id, subscription2.id)

    def test_remove_structural_subscription(self):
        # an unprivileged user cannot unsubscribe a team
        login_person(self.ordinary_subscriber)
        self.assertRaises(UserCannotSubscribePerson,
            self.target.removeBugSubscription,
            self.team, self.ordinary_subscriber)

    def test_remove_nonexistant_structural_subscription(self):
        # removing a nonexistant subscription raises a
        # DeleteSubscriptionError
        login_person(self.ordinary_subscriber)
        self.assertRaises(DeleteSubscriptionError,
            self.target.removeBugSubscription,
            self.ordinary_subscriber, self.ordinary_subscriber)


class UnrestrictedStructuralSubscription(StructuralSubscriptionTestBase):

    def test_structural_subscription_by_ordinary_user(self):
        # ordinary users can subscribe themselves
        login_person(self.ordinary_subscriber)
        self.assertIsInstance(
            self.target.addBugSubscription(
                self.ordinary_subscriber, self.ordinary_subscriber),
            StructuralSubscription)

    def test_remove_structural_subscription_by_ordinary_user(self):
        # ordinary users can unsubscribe themselves
        login_person(self.ordinary_subscriber)
        self.assertIsInstance(
            self.target.addBugSubscription(
                self.ordinary_subscriber, self.ordinary_subscriber),
            StructuralSubscription)
        self.assertEqual(
            self.target.removeBugSubscription(
                self.ordinary_subscriber, self.ordinary_subscriber),
            None)

    def test_team_structural_subscription_by_team_owner(self):
        # team owners can subscribe their team
        login_person(self.team_owner)
        self.assertIsInstance(
            self.target.addBugSubscription(
                self.team, self.team_owner),
            StructuralSubscription)

    def test_remove_team_structural_subscription_by_team_owner(self):
        # team owners can unsubscribe their team
        login_person(self.team_owner)
        self.assertIsInstance(
            self.target.addBugSubscription(
                self.team, self.team_owner),
            StructuralSubscription)
        self.assertEqual(
            self.target.removeBugSubscription(
                self.team, self.team_owner),
            None)


class TestStructuralSubscriptionForDistro(StructuralSubscriptionTestBase,
    TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForDistro, self).setUp()
        self.target = self.factory.makeDistribution()
        naked_distro = removeSecurityProxy(self.target)
        naked_distro.bug_supervisor = self.bug_supervisor_subscriber

    def test_distribution_subscription_by_ordinary_user(self):
        # ordinary users can not subscribe themselves to a distribution
        login_person(self.ordinary_subscriber)
        self.assertRaises(UserCannotSubscribePerson,
            self.target.addBugSubscription,
            self.ordinary_subscriber, self.ordinary_subscriber)

    def test_team_distribution_structural_subscription_by_team_owner(self):
        # team owners cannot subscribe their team to a distribution
        login_person(self.team_owner)
        self.assertRaises(UserCannotSubscribePerson,
            self.target.addBugSubscription,
            self.team, self.team_owner)

    def test_distribution_subscription_by_bug_supervisor(self):
        # bug supervisor can subscribe themselves
        login_person(self.bug_supervisor_subscriber)
        self.assertIsInstance(
            self.target.addBugSubscription(
                    self.bug_supervisor_subscriber,
                    self.bug_supervisor_subscriber),
            StructuralSubscription)

    def test_distribution_subscription_by_bug_supervisor_team(self):
        # team admins can subscribe team if team is bug supervisor
        removeSecurityProxy(self.target).bug_supervisor = self.team
        login_person(self.team_owner)
        self.assertIsInstance(
                self.target.addBugSubscription(self.team, self.team_owner),
                    StructuralSubscription)

    def test_distribution_unsubscription_by_bug_supervisor_team(self):
        # team admins can unsubscribe team if team is bug supervisor
        removeSecurityProxy(self.target).bug_supervisor = self.team
        login_person(self.team_owner)
        self.assertIsInstance(
                self.target.addBugSubscription(self.team, self.team_owner),
                    StructuralSubscription)
        self.assertEqual(
                self.target.removeBugSubscription(self.team, self.team_owner),
                    None)

    def test_distribution_subscription_without_bug_supervisor(self):
        # for a distribution without a bug supervisor anyone can
        # subscribe
        removeSecurityProxy(self.target).bug_supervisor = None
        login_person(self.ordinary_subscriber)
        self.assertIsInstance(
            self.target.addBugSubscription(
                self.ordinary_subscriber, self.ordinary_subscriber),
            StructuralSubscription)


class TestStructuralSubscriptionForProduct(
    UnrestrictedStructuralSubscription, TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForProduct, self).setUp()
        self.target = self.factory.makeProduct()


class TestStructuralSubscriptionForDistroSourcePackage(
    UnrestrictedStructuralSubscription, TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForDistroSourcePackage, self).setUp()
        self.target = self.factory.makeDistributionSourcePackage()
        self.target = ProxyFactory(self.target)


class TestStructuralSubscriptionForMilestone(
    UnrestrictedStructuralSubscription, TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForMilestone, self).setUp()
        self.target = self.factory.makeMilestone()
        self.target = ProxyFactory(self.target)


class TestStructuralSubscriptionForDistroSeries(
    UnrestrictedStructuralSubscription, TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForDistroSeries, self).setUp()
        self.target = self.factory.makeDistroSeries()
        self.target = ProxyFactory(self.target)


def distributionSourcePackageSetUp(test):
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['target'] = ubuntu.getSourcePackage('evolution')
    test.globs['other_target'] = ubuntu.getSourcePackage('pmount')
    test.globs['filebug'] = bugtarget_filebug


def productSetUp(test):
    setUp(test)
    test.globs['target'] = getUtility(IProductSet).getByName('firefox')
    test.globs['filebug'] = bugtarget_filebug


def distributionSetUp(test):
    setUp(test)
    test.globs['target'] = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['filebug'] = bugtarget_filebug


def milestone_filebug(milestone, summary, status=None):
    bug = bugtarget_filebug(milestone.target, summary, status=status)
    bug.bugtasks[0].milestone = milestone
    return bug


def milestoneSetUp(test):
    setUp(test)
    firefox = getUtility(IProductSet).getByName('firefox')
    test.globs['target'] = firefox.getMilestone('1.0')
    test.globs['filebug'] = milestone_filebug


def distroseries_sourcepackage_filebug(distroseries, summary, status=None):
    params = CreateBugParams(
        getUtility(ILaunchBag).user, summary, comment=summary, status=status)
    alsa_utils = getUtility(ISourcePackageNameSet)['alsa-utils']
    params.setBugTarget(distribution=distroseries.distribution,
                        sourcepackagename=alsa_utils)
    bug = distroseries.distribution.createBug(params)
    nomination = bug.addNomination(
        distroseries.distribution.owner, distroseries)
    nomination.approve(distroseries.distribution.owner)
    return bug


def distroSeriesSourcePackageSetUp(test):
    setUp(test)
    test.globs['target'] = (
        getUtility(IDistributionSet).getByName('ubuntu').getSeries('hoary'))
    test.globs['filebug'] = distroseries_sourcepackage_filebug


def test_suite():
    """Return the `IStructuralSubscriptionTarget` TestSuite."""
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))

    setUpMethods = [
        distributionSourcePackageSetUp,
        productSetUp,
        distributionSetUp,
        milestoneSetUp,
        distroSeriesSourcePackageSetUp,
        ]

    for setUpMethod in setUpMethods:
        test = LayeredDocFileSuite('structural-subscription-target.txt',
            setUp=setUpMethod, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)

    return suite
