__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import ProxyFactory, removeSecurityProxy
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.webapp.testing import verifyObject
from lp.testing import (
    ANONYMOUS, login, login_person, TestCaseWithFactory)
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.structuralsubscription import (
    IStructuralSubscriptionTarget, UserCannotSubscribePerson)
from lp.registry.model.structuralsubscription import StructuralSubscription


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
        login('foo.bar@canonical.com')
        foobar = getUtility(IPersonSet).getByEmail('foo.bar@canonical.com')
        #with celebrity_logged_in('admin'):
        self.assertIsInstance(
            self.target.addBugSubscription(self.ordinary_subscriber, foobar),
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


class UnrestrictedStructuralSubscription(StructuralSubscriptionTestBase):

    def test_structural_subscription_by_ordinary_user(self):
        # ordinary users can subscribe themselves
        login_person(self.ordinary_subscriber)
        self.assertIsInstance(
            self.target.addBugSubscription(
                self.ordinary_subscriber, self.ordinary_subscriber),
            StructuralSubscription)

    def test_team_structural_subscription_by_team_owner(self):
        # team owners can subscribe their team
        login_person(self.team_owner)
        self.assertIsInstance(
            self.target.addBugSubscription(
                self.team, self.team_owner),
            StructuralSubscription)


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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
