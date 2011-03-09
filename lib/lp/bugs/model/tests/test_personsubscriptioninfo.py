# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the personsubscriptioninfo module."""

__metaclass__ = type

from storm.store import Store
from zope.security.interfaces import Unauthorized
from zope.security.proxy import ProxyFactory, removeSecurityProxy

from canonical.launchpad import searchbuilder
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.testing import DatabaseFunctionalLayer
from lp.bugs.enum import BugNotificationLevel
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.interfaces.personsubscriptioninfo import (
    PersonSubscriptionType,
    )
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.model.personsubscriptioninfo import PersonSubscriptions
from lp.registry.interfaces.teammembership import TeamMembershipStatus
from lp.testing import (
    anonymous_logged_in,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )

class TestPersonSubscriptionInfo(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSubscriptionInfo, self).setUp()
        self.subscriber = self.factory.makePerson()
        self.bug = self.factory.makeBug()
        self.subscriptions = PersonSubscriptions(self.subscriber, self.bug)

    def test_no_subscriptions(self):
        # Load a `PersonSubscriptionInfo`s for a subscriber and a bug.
        self.subscriptions.reload()

        self.assertIs(None, self.subscriptions.direct_subscriptions)
        self.assertIs(None, self.subscriptions.duplicate_subscriptions)
        self.assertIs(None, self.subscriptions.supervisor_subscriptions)

    def test_direct(self):
        # Subscribed directly to the bug.
        with person_logged_in(self.subscriber):
            self.bug.subscribe(self.subscriber, self.subscriber)

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.direct_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.DIRECT,
            self.subscriptions.direct_subscriptions.subscription_type)
        self.assertTrue(self.subscriptions.direct_subscriptions.personally)

    def test_direct_through_team(self):
        # Subscribed to the bug through membership in a team.
        team = self.factory.makeTeam(members=[self.subscriber])
        with person_logged_in(self.subscriber):
            self.bug.subscribe(team, self.subscriber)

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.direct_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.DIRECT,
            self.subscriptions.direct_subscriptions.subscription_type)
        self.assertFalse(self.subscriptions.direct_subscriptions.personally)
        self.assertContentEqual(
            [team], self.subscriptions.direct_subscriptions.as_team_member)

    def test_direct_through_team_as_admin(self):
        # Subscribed to the bug through membership in a team
        # as an admin of that team.
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.addMember(self.subscriber, team.teamowner,
                           status=TeamMembershipStatus.ADMIN)
            self.bug.subscribe(team, team.teamowner)

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.direct_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.DIRECT,
            self.subscriptions.direct_subscriptions.subscription_type)
        self.assertFalse(self.subscriptions.direct_subscriptions.personally)
        self.assertContentEqual(
            [team], self.subscriptions.direct_subscriptions.as_team_admin)

    def test_duplicate_direct(self):
        # Subscribed directly to the duplicate bug.
        duplicate = self.factory.makeBug()
        with person_logged_in(self.subscriber):
            duplicate.markAsDuplicate(self.bug)
            duplicate.subscribe(self.subscriber, self.subscriber)
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.duplicate_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.DUPLICATE,
            self.subscriptions.duplicate_subscriptions.subscription_type)
        self.assertContentEqual(
            [duplicate], self.subscriptions.duplicate_subscriptions.duplicates)
        self.assertTrue(self.subscriptions.duplicate_subscriptions.personally)

    def test_duplicate_direct_reverse(self):
        # Subscribed directly to the primary bug, and a duplicate bug changes.
        duplicate = self.factory.makeBug()
        with person_logged_in(self.subscriber):
            self.bug.markAsDuplicate(duplicate)
            duplicate.subscribe(self.subscriber, self.subscriber)
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.duplicate_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.DUPLICATE,
            self.subscriptions.duplicate_subscriptions.subscription_type)
        self.assertContentEqual(
            [duplicate], self.subscriptions.duplicate_subscriptions.duplicates)
        self.assertTrue(self.subscriptions.duplicate_subscriptions.personally)

    def test_duplicate_multiple(self):
        # Subscribed directly to more than one duplicate bug.
        duplicate1 = self.factory.makeBug()
        duplicate2 = self.factory.makeBug()
        with person_logged_in(self.subscriber):
            duplicate1.markAsDuplicate(self.bug)
            duplicate1.subscribe(self.subscriber, self.subscriber)
            duplicate2.markAsDuplicate(self.bug)
            duplicate2.subscribe(self.subscriber, self.subscriber)
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.duplicate_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.DUPLICATE,
            self.subscriptions.duplicate_subscriptions.subscription_type)
        self.assertContentEqual(
            [duplicate1, duplicate2],
            self.subscriptions.duplicate_subscriptions.duplicates)
        self.assertTrue(self.subscriptions.duplicate_subscriptions.personally)

    def test_duplicate_through_team(self):
        # Subscribed to a duplicate bug through team membership.
        team = self.factory.makeTeam(members=[self.subscriber])
        duplicate = self.factory.makeBug()
        with person_logged_in(self.subscriber):
            duplicate.markAsDuplicate(self.bug)
            duplicate.subscribe(team, self.subscriber)
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.duplicate_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.DUPLICATE,
            self.subscriptions.duplicate_subscriptions.subscription_type)
        self.assertContentEqual(
            [duplicate], self.subscriptions.duplicate_subscriptions.duplicates)
        self.assertFalse(self.subscriptions.duplicate_subscriptions.personally)
        self.assertContentEqual(
            [team], self.subscriptions.duplicate_subscriptions.as_team_member)

    def test_duplicate_through_team_as_admin(self):
        # Subscribed to a duplicate bug through team membership
        # as an admin of that team.
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.addMember(self.subscriber, team.teamowner,
                           status=TeamMembershipStatus.ADMIN)
        duplicate = self.factory.makeBug()
        with person_logged_in(self.subscriber):
            duplicate.markAsDuplicate(self.bug)
            duplicate.subscribe(team, self.subscriber)
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.duplicate_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.DUPLICATE,
            self.subscriptions.duplicate_subscriptions.subscription_type)
        self.assertContentEqual(
            [duplicate], self.subscriptions.duplicate_subscriptions.duplicates)
        self.assertFalse(self.subscriptions.duplicate_subscriptions.personally)
        self.assertContentEqual(
            [team], self.subscriptions.duplicate_subscriptions.as_team_admin)

    def test_supervisor_owner(self):
        # Bug is targetted to a pillar with no supervisor set.
        target = self.bug.default_bugtask.target
        # Load a `PersonSubscriptionInfo`s for target.owner and a bug.
        self.subscriptions.loadSubscriptionsFor(target.owner, self.bug)

        self.assertIsNot(None, self.subscriptions.supervisor_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.SUPERVISOR,
            self.subscriptions.supervisor_subscriptions.subscription_type)
        self.assertContentEqual(
            [target], self.subscriptions.supervisor_subscriptions.owner_for)

    def test_supervisor_direct(self):
        # Bug is targetted to a pillar with subscriber as the bug supervisor.
        target = self.bug.default_bugtask.target
        removeSecurityProxy(target).bug_supervisor = self.subscriber
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.supervisor_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.SUPERVISOR,
            self.subscriptions.supervisor_subscriptions.subscription_type)
        self.assertContentEqual(
            [target], self.subscriptions.supervisor_subscriptions.supervisor_for)
        self.assertTrue(self.subscriptions.supervisor_subscriptions.personally)

    def test_supervisor_multiple(self):
        # Bug has two bug tasks targetted to pillars which
        # subscriber is a supervisor for.
        target = self.bug.default_bugtask.target
        removeSecurityProxy(target).bug_supervisor = self.subscriber
        second_bugtask = self.factory.makeBugTask(bug=self.bug)
        second_target = second_bugtask.target
        removeSecurityProxy(second_target).bug_supervisor = self.subscriber

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.supervisor_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.SUPERVISOR,
            self.subscriptions.supervisor_subscriptions.subscription_type)
        self.assertContentEqual(
            [target, second_target],
            self.subscriptions.supervisor_subscriptions.supervisor_for)

    def test_supervisor_through_team(self):
        # Bug is targetted to a pillar and subscriber is a member
        # of a bug supervisor team.
        target = self.bug.default_bugtask.target
        team = self.factory.makeTeam(members=[self.subscriber])
        removeSecurityProxy(target).bug_supervisor = team
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.supervisor_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.SUPERVISOR,
            self.subscriptions.supervisor_subscriptions.subscription_type)
        self.assertContentEqual(
            [target], self.subscriptions.supervisor_subscriptions.supervisor_for)
        self.assertFalse(self.subscriptions.supervisor_subscriptions.personally)
        self.assertContentEqual(
            [team], self.subscriptions.supervisor_subscriptions.as_team_member)

    def test_supervisor_through_team_as_admin(self):
        # Bug is targetted to a pillar and subscriber is an admin
        # of a bug supervisor team.
        target = self.bug.default_bugtask.target
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.addMember(self.subscriber, team.teamowner,
                           status=TeamMembershipStatus.ADMIN)
        removeSecurityProxy(target).bug_supervisor = team
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertIsNot(None, self.subscriptions.supervisor_subscriptions)
        self.assertEqual(
            PersonSubscriptionType.SUPERVISOR,
            self.subscriptions.supervisor_subscriptions.subscription_type)
        self.assertContentEqual(
            [target], self.subscriptions.supervisor_subscriptions.supervisor_for)
        self.assertContentEqual(
            [team], self.subscriptions.supervisor_subscriptions.as_team_admin)
