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
    IDirectSubscriptionInfoCollection,
    IRealSubscriptionInfo,
    IVirtualSubscriptionInfo,
    IVirtualSubscriptionInfoCollection,
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
from lp.testing.matchers import Provides

class TestPersonSubscriptionInfo(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonSubscriptionInfo, self).setUp()
        self.subscriber = self.factory.makePerson()
        self.bug = self.factory.makeBug()
        self.subscriptions = PersonSubscriptions(self.subscriber, self.bug)

    def assertCollectionsAreNone(self, except_=None):
        names = ('direct', 'from_duplicate', 'as_owner', 'as_assignee')
        assert except_ is None or except_ in names
        for name in names:
            if name == except_:
                collection = getattr(self.subscriptions, name)
                self.assertIsNot(None, collection)
                self.assertEqual(self.subscriptions.count, collection.count)
            else:
                self.assertIs(None, getattr(self.subscriptions, name))

    def assertCollectionContents(
        self, collection,
        personal=0, as_team_member=0, as_team_admin=0):
        # Make sure that the collection has the values we expect.
        self.assertEqual(collection.count,
                         personal + as_team_member + as_team_admin)
        for name, expected in (('personal', personal),
                            ('as_team_member', as_team_member),
                            ('as_team_admin', as_team_admin)):
            actual = getattr(collection, name)
            if (name=='personal' and
                IDirectSubscriptionInfoCollection.providedBy(collection)):
                # This is the only one that is not a collection.
                if expected == 1:
                    self.assertThat(actual, Provides(IRealSubscriptionInfo))
                else:
                    assert expected == 0
                    self.assertIs(None, actual)
            else:
                self.assertEqual(expected, len(actual))
                if IVirtualSubscriptionInfoCollection.providedBy(collection):
                    expected_interface = IVirtualSubscriptionInfo
                else:
                    expected_interface = IRealSubscriptionInfo
                for info in actual:
                    self.assertThat(info, Provides((expected_interface)))

    def assertVirtualSubscriptionInfoMatches(
        self, info, bug, principal, pillar, bugtasks):
        # Make sure that the virtual subscription info has expected values.
        self.assertEqual(info.bug, bug)
        self.assertEqual(info.principal, principal)
        self.assertEqual(info.pillar, pillar)
        self.assertContentEqual(info.tasks, bugtasks)

    def assertRealSubscriptionInfoMatches(
        self, info, bug, principal,
        principal_is_reporter, security_contact_tasks, bug_supervisor_tasks):
        # Make sure that the real subscription info has expected values.
        self.assertEqual(info.bug, bug)
        self.assertEqual(info.principal, principal)
        self.assertEqual(info.principal_is_reporter, principal_is_reporter)
        self.assertContentEqual(
            info.bug_supervisor_tasks, bug_supervisor_tasks)
        self.assertContentEqual(
            info.security_contact_tasks, security_contact_tasks)

    def test_no_subscriptions(self):
        # Load a `PersonSubscriptionInfo`s for a subscriber and a bug.
        self.subscriptions.reload()
        self.assertCollectionsAreNone()
        self.failIf(self.subscriptions.muted)

    def test_assignee(self):
        with person_logged_in(self.subscriber):
            self.bug.default_bugtask.transitionToAssignee(self.subscriber)
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='as_assignee')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.as_assignee, personal=1)
        self.assertVirtualSubscriptionInfoMatches(
            self.subscriptions.as_assignee.personal[0],
            self.bug, self.subscriber,
            self.bug.default_bugtask.target, [self.bug.default_bugtask])

    def test_assignee_through_team(self):
        team = self.factory.makeTeam(members=[self.subscriber])
        with person_logged_in(self.subscriber):
            self.bug.bugtasks[0].transitionToAssignee(team)
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='as_assignee')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.as_assignee, as_team_member=1)
        self.assertVirtualSubscriptionInfoMatches(
            self.subscriptions.as_assignee.as_team_member[0],
            self.bug, team,
            self.bug.default_bugtask.target, [self.bug.default_bugtask])

    def test_assignee_through_team_as_admin(self):
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.addMember(self.subscriber, team.teamowner,
                           status=TeamMembershipStatus.ADMIN)
            self.bug.bugtasks[0].transitionToAssignee(team)
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='as_assignee')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.as_assignee, as_team_admin=1)
        self.assertVirtualSubscriptionInfoMatches(
            self.subscriptions.as_assignee.as_team_admin[0],
            self.bug, team,
            self.bug.default_bugtask.target, [self.bug.default_bugtask])

    def test_direct(self):
        # Subscribed directly to the bug.
        with person_logged_in(self.subscriber):
            self.bug.subscribe(self.subscriber, self.subscriber)

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='direct')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.direct, personal=1)
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.direct.personal,
            self.bug, self.subscriber, False, [], [])

    def test_direct_through_team(self):
        # Subscribed to the bug through membership in a team.
        team = self.factory.makeTeam(members=[self.subscriber])
        with person_logged_in(self.subscriber):
            self.bug.subscribe(team, self.subscriber)

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='direct')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.direct, as_team_member=1)
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.direct.as_team_member[0],
            self.bug, team, False, [], [])

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

        self.assertCollectionsAreNone(except_='direct')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.direct, as_team_admin=1)
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.direct.as_team_admin[0],
            self.bug, team, False, [], [])

    def test_duplicate_direct(self):
        # Subscribed directly to the duplicate bug.
        duplicate = self.factory.makeBug()
        with person_logged_in(self.subscriber):
            duplicate.markAsDuplicate(self.bug)
            duplicate.subscribe(self.subscriber, self.subscriber)
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='from_duplicate')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.from_duplicate, personal=1)
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.from_duplicate.personal[0],
            duplicate, self.subscriber, False, [], [])

    def test_duplicate_direct_reverse(self):
        # Subscribed directly to the primary bug, and a duplicate bug changes.
        duplicate = self.factory.makeBug()
        with person_logged_in(self.subscriber):
            self.bug.markAsDuplicate(duplicate)
            duplicate.subscribe(self.subscriber, self.subscriber)
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='from_duplicate')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.from_duplicate, personal=1)
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.from_duplicate.personal[0],
            duplicate, self.subscriber, False, [], [])

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

        self.assertCollectionsAreNone(except_='from_duplicate')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.from_duplicate, personal=2)
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.from_duplicate.personal[0],
            duplicate1, self.subscriber, False, [], [])
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.from_duplicate.personal[1],
            duplicate2, self.subscriber, False, [], [])

    def test_duplicate_through_team(self):
        # Subscribed to a duplicate bug through team membership.
        team = self.factory.makeTeam(members=[self.subscriber])
        duplicate = self.factory.makeBug()
        with person_logged_in(self.subscriber):
            duplicate.markAsDuplicate(self.bug)
            duplicate.subscribe(team, self.subscriber)
        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='from_duplicate')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.from_duplicate, as_team_member=1)
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.from_duplicate.as_team_member[0],
            duplicate, team, False, [], [])

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

        self.assertCollectionsAreNone(except_='from_duplicate')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.from_duplicate, as_team_admin=1)
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.from_duplicate.as_team_admin[0],
            duplicate, team, False, [], [])

    def test_subscriber_is_reporter(self):
        self.bug = self.factory.makeBug(owner=self.subscriber)
        self.subscriptions = PersonSubscriptions(self.subscriber, self.bug)
        # Subscribed directly to the bug.
        with person_logged_in(self.subscriber):
            self.bug.subscribe(self.subscriber, self.subscriber)

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.direct.personal,
            self.bug, self.subscriber, True, [], [])

    def test_subscriber_is_security_contact(self):
        target = self.bug.default_bugtask.target
        removeSecurityProxy(target).security_contact = self.subscriber
        # Subscribed directly to the bug.
        with person_logged_in(self.subscriber):
            self.bug.subscribe(self.subscriber, self.subscriber)

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.direct.personal,
            self.bug, self.subscriber, False,
             [{'task': self.bug.default_bugtask, 'pillar': target}], [])

    def test_subscriber_is_bug_supervisor(self):
        target = self.bug.default_bugtask.target
        removeSecurityProxy(target).bug_supervisor = self.subscriber
        # Subscribed directly to the bug.
        with person_logged_in(self.subscriber):
            self.bug.subscribe(self.subscriber, self.subscriber)

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()
        self.assertRealSubscriptionInfoMatches(
            self.subscriptions.direct.personal,
            self.bug, self.subscriber, False,
             [], [{'task': self.bug.default_bugtask, 'pillar': target}])

    def test_owner(self):
        # Bug is targeted to a pillar with no supervisor set.
        target = self.bug.default_bugtask.target
        # Load a `PersonSubscriptionInfo`s for target.owner and a bug.
        self.subscriptions.loadSubscriptionsFor(target.owner, self.bug)

        self.assertCollectionsAreNone(except_='as_owner')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.as_owner, personal=1)
        self.assertVirtualSubscriptionInfoMatches(
            self.subscriptions.as_owner.personal[0],
            self.bug, target.owner,
            self.bug.default_bugtask.target, [self.bug.default_bugtask])

    def test_owner_as_bug_supervisor_is_empty(self):
        target = self.bug.default_bugtask.target
        removeSecurityProxy(target).bug_supervisor = target.owner
        # Subscribed directly to the bug.
        self.subscriptions.loadSubscriptionsFor(target.owner, self.bug)
        self.assertCollectionsAreNone()
        self.failIf(self.subscriptions.muted)

    def test_owner_through_team(self):
        # Bug is targeted to a pillar with no supervisor set.
        target = self.bug.default_bugtask.target
        team = self.factory.makeTeam(members=[self.subscriber])
        removeSecurityProxy(target).owner = team
        # Load a `PersonSubscriptionInfo`s for target.owner and a bug.
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='as_owner')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.as_owner, as_team_member=1)
        self.assertVirtualSubscriptionInfoMatches(
            self.subscriptions.as_owner.as_team_member[0],
            self.bug, target.owner,
            self.bug.default_bugtask.target, [self.bug.default_bugtask])

    def test_owner_through_team_as_admin(self):
        # Bug is targeted to a pillar with no supervisor set.
        target = self.bug.default_bugtask.target
        team = self.factory.makeTeam()
        with person_logged_in(team.teamowner):
            team.addMember(self.subscriber, team.teamowner,
                           status=TeamMembershipStatus.ADMIN)
        removeSecurityProxy(target).owner = team
        # Load a `PersonSubscriptionInfo`s for target.owner and a bug.
        self.subscriptions.reload()

        self.assertCollectionsAreNone(except_='as_owner')
        self.failIf(self.subscriptions.muted)
        self.assertCollectionContents(
            self.subscriptions.as_owner, as_team_admin=1)
        self.assertVirtualSubscriptionInfoMatches(
            self.subscriptions.as_owner.as_team_admin[0],
            self.bug, target.owner,
            self.bug.default_bugtask.target, [self.bug.default_bugtask])

    def test_is_muted(self):
        # Subscribed directly to the bug, muted.
        with person_logged_in(self.subscriber):
            self.bug.subscribe(self.subscriber, self.subscriber,
                               level=BugNotificationLevel.NOTHING)

        # Load a `PersonSubscriptionInfo`s for subscriber and a bug.
        self.subscriptions.reload()

        self.failUnless(self.subscriptions.muted)
