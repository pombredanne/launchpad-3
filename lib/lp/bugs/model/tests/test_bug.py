# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.person import PersonVisibility
from lp.registry.model.structuralsubscription import StructuralSubscription
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )


class TestBug(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_get_subscribers_for_person_unsubscribed(self):
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        self.assertTrue(bug.getSubscribersForPerson(person).is_empty())

    def test_get_subscribers_for_person_direct_subscription(self):
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        with person_logged_in(person):
            bug.subscribe(person, person)
        self.assertEqual([person], list(bug.getSubscribersForPerson(person)))

    def test_get_subscribers_for_person_indirect_subscription(self):
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        [team1, team2] = (
            self.factory.makeTeam(members=[person]),
            self.factory.makeTeam(members=[person]))
        with person_logged_in(person):
            bug.subscribe(team1, person)
        self.assertEqual([team1], list(bug.getSubscribersForPerson(person)))

    def test_get_subscribers_for_person_many_subscriptions(self):
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        team1 = self.factory.makeTeam(members=[person])
        team2 = self.factory.makeTeam(members=[person])
        with person_logged_in(person):
            bug.subscribe(team1, person)
            bug.subscribe(team2, person)
            bug.subscribe(person, person)
        self.assertEqual(
            set([person, team1, team2]),
            set(bug.getSubscribersForPerson(person)))

    def test_get_subscribers_for_person_from_duplicates_too(self):
        bug = self.factory.makeBug()
        real_bug = self.factory.makeBug()
        person = self.factory.makePerson()
        team1 = self.factory.makeTeam(members=[person])
        team2 = self.factory.makeTeam(members=[person])
        with person_logged_in(person):
            bug.subscribe(team1, person)
            bug.subscribe(team2, person)
            bug.subscribe(person, person)
            bug.markAsDuplicate(real_bug)
        self.assertEqual(
            set([person, team1, team2]),
            set(real_bug.getSubscribersForPerson(person)))

    def test_getSubscriptionsFromDuplicates(self):
        # getSubscriptionsFromDuplicates() will return only the earliest
        # subscription if a user is subscribed to a bug via more than one
        # duplicate.
        user = self.factory.makePerson()
        login_person(user)
        bug = self.factory.makeBug(owner=user)
        dupe1 = self.factory.makeBug(owner=user)
        dupe1.markAsDuplicate(bug)
        subscription = dupe1.subscribe(user, user)
        dupe2 = self.factory.makeBug(owner=user)
        dupe2.markAsDuplicate(bug)
        dupe2.subscribe(user, user)
        self.assertEqual(
            [subscription], list(bug.getSubscriptionsFromDuplicates()))

    def test_get_also_notified_subscribers_with_private_team(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        member = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=member, visibility=PersonVisibility.PRIVATE)
        StructuralSubscription(
            product=product, subscriber=team, subscribed_by=member)
        self.assertTrue(team in bug.getAlsoNotifiedSubscribers())

    def test_get_indirect_subscribers_with_private_team(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        member = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=member, visibility=PersonVisibility.PRIVATE)
        StructuralSubscription(
            product=product, subscriber=team, subscribed_by=member)
        self.assertTrue(team in bug.getIndirectSubscribers())

    def test_get_direct_subscribers_with_private_team(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        member = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=member, visibility=PersonVisibility.PRIVATE)
        with person_logged_in(member):
            bug.subscribe(team, member)
        self.assertTrue(team in bug.getDirectSubscribers())

    def test_get_subscribers_from_duplicates_with_private_team(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        dupe_bug = self.factory.makeBug()
        member = self.factory.makePerson()
        team = self.factory.makeTeam(
            owner=member, visibility=PersonVisibility.PRIVATE)
        with person_logged_in(member):
            dupe_bug.subscribe(team, member)
            dupe_bug.markAsDuplicate(bug)
        self.assertTrue(team in bug.getSubscribersFromDuplicates())


class TestBugStructuralSubscribers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_getStructuralSubscribers_no_subscribers(self):
        # If there are no subscribers for any of the bug's targets then no
        # subscribers will be returned by getStructuralSubscribers().
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        self.assertEqual([], list(bug.getStructuralSubscribers()))

    def test_getStructuralSubscribers_single_target(self):
        # Subscribers for any of the bug's targets are returned.
        subscriber = self.factory.makePerson()
        login_person(subscriber)
        product = self.factory.makeProduct()
        product.addBugSubscription(subscriber, subscriber)
        bug = self.factory.makeBug(product=product)
        self.assertEqual([subscriber], list(bug.getStructuralSubscribers()))

    def test_getStructuralSubscribers_multiple_targets(self):
        # Subscribers for any of the bug's targets are returned.
        actor = self.factory.makePerson()
        login_person(actor)

        subscriber1 = self.factory.makePerson()
        subscriber2 = self.factory.makePerson()

        product1 = self.factory.makeProduct(owner=actor)
        product1.addBugSubscription(subscriber1, subscriber1)
        product2 = self.factory.makeProduct(owner=actor)
        product2.addBugSubscription(subscriber2, subscriber2)

        bug = self.factory.makeBug(product=product1)
        bug.addTask(actor, product2)

        self.assertEqual(
            set([subscriber1, subscriber2]),
            set(bug.getStructuralSubscribers()))

    def test_getStructuralSubscribers_level(self):
        # getStructuralSubscribers() respects the given level.
        subscriber = self.factory.makePerson()
        login_person(subscriber)
        product = self.factory.makeProduct()
        subscription = product.addBugSubscription(subscriber, subscriber)
        subscription.bug_notification_level = BugNotificationLevel.METADATA
        bug = self.factory.makeBug(product=product)
        self.assertEqual(
            [subscriber], list(
                bug.getStructuralSubscribers(
                    level=BugNotificationLevel.METADATA)))
        subscription.bug_notification_level = BugNotificationLevel.METADATA
        self.assertEqual(
            [], list(
                bug.getStructuralSubscribers(
                    level=BugNotificationLevel.COMMENTS)))
