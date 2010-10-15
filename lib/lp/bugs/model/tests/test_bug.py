# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

__metaclass__ = type

from storm.store import ResultSet

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.mail.bugnotificationrecipients import BugNotificationRecipients
from lp.registry.enum import BugNotificationLevel
from lp.registry.interfaces.person import PersonVisibility
from lp.registry.model.structuralsubscription import StructuralSubscription
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.matchers import StartsWith


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
        team1 = self.factory.makeTeam(members=[person])
        self.factory.makeTeam(members=[person])
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

    def test_subscribe_with_level(self):
        # It's possible to subscribe to a bug at a different
        # BugNotificationLevel by passing a `level` parameter to
        # subscribe().
        bug = self.factory.makeBug()
        for level in BugNotificationLevel.items:
            subscriber = self.factory.makePerson()
            with person_logged_in(subscriber):
                subscription = bug.subscribe(
                    subscriber, subscriber, level=level)
            self.assertEqual(level, subscription.bug_notification_level)

    def test_get_direct_subscribers_with_level(self):
        # It's possible to pass a level parameter to
        # getDirectSubscribers() to filter the subscribers returned.
        # When a `level` is passed to getDirectSubscribers(), the
        # subscribers returned will be those of that level of
        # subscription or higher.
        bug = self.factory.makeBug()
        # We unsubscribe the bug's owner because if we don't there will
        # be two COMMENTS-level subscribers.
        with person_logged_in(bug.owner):
            bug.unsubscribe(bug.owner, bug.owner)
        reversed_levels = sorted(
            BugNotificationLevel.items, reverse=True)
        subscribers = []
        for level in reversed_levels:
            subscriber = self.factory.makePerson()
            subscribers.append(subscriber)
            with person_logged_in(subscriber):
                subscription = bug.subscribe(
                    subscriber, subscriber, level=level)
            direct_subscribers = bug.getDirectSubscribers(level=level)

            # All the previous subscribers will be included because
            # their level of subscription is such that they also receive
            # notifications at the current level.
            self.assertEqual(
                set(subscribers), set(direct_subscribers),
                "Subscribers did not match expected value.")

    def test_get_direct_subscribers_default_level(self):
        # If no `level` parameter is passed to getDirectSubscribers(),
        # the assumed `level` is BugNotification.NOTHING.
        bug = self.factory.makeBug()
        # We unsubscribe the bug's owner because if we don't there will
        # be two COMMENTS-level subscribers.
        with person_logged_in(bug.owner):
            bug.unsubscribe(bug.owner, bug.owner)
        subscribers = []
        for level in BugNotificationLevel.items:
            subscriber = self.factory.makePerson()
            subscribers.append(subscriber)
            with person_logged_in(subscriber):
                subscription = bug.subscribe(
                    subscriber, subscriber, level=level)

        # All the subscribers should be returned by
        # getDirectSubscribers() because it defaults to returning
        # subscribers at level NOTHING, which everything is higher than.
        direct_subscribers = bug.getDirectSubscribers()
        self.assertEqual(
            set(subscribers), set(direct_subscribers),
            "Subscribers did not match expected value.")

    def test_subscribers_from_dupes_uses_level(self):
        # When getSubscribersFromDuplicates() is passed a `level`
        # parameter it will include only subscribers subscribed to
        # duplicates at that BugNotificationLevel or higher.
        bug = self.factory.makeBug()
        duplicate_bug = self.factory.makeBug()
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(bug)
            # We unsubscribe the owner of the duplicate to avoid muddling
            # the results retuned by getSubscribersFromDuplicates()
            duplicate_bug.unsubscribe(
                duplicate_bug.owner, duplicate_bug.owner)
        reversed_levels = sorted(
            BugNotificationLevel.items, reverse=True)
        subscribers = []
        for level in reversed_levels:
            subscriber = self.factory.makePerson()
            subscribers.append(subscriber)
            with person_logged_in(subscriber):
                subscription = duplicate_bug.subscribe(
                    subscriber, subscriber, level=level)
            duplicate_subscribers = (
                bug.getSubscribersFromDuplicates(level=level))
            # All the previous subscribers will be included because
            # their level of subscription is such that they also receive
            # notifications at the current level.
            self.assertEqual(
                set(subscribers), set(duplicate_subscribers),
                "Number of subscribers did not match expected value.")

    def test_subscribers_from_dupes_overrides_using_level(self):
        # Bug.getSubscribersFromDuplicates() does not return subscribers
        # who also have a direct subscription to the master bug provided
        # that the subscription to the master bug is of the same level
        # or higher as the subscription to the duplicate.
        bug = self.factory.makeBug()
        duplicate_bug = self.factory.makeBug()
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(bug)
            # We unsubscribe the owner of the duplicate to avoid muddling
            # the results retuned by getSubscribersFromDuplicates()
            duplicate_bug.unsubscribe(
                duplicate_bug.owner, duplicate_bug.owner)
        subscriber = self.factory.makePerson()
        with person_logged_in(subscriber):
            direct_subscription = bug.subscribe(
                subscriber, subscriber, level=BugNotificationLevel.NOTHING)
            dupe_subscription = duplicate_bug.subscribe(
                subscriber, subscriber, level=BugNotificationLevel.METADATA)
        duplicate_subscribers = bug.getSubscribersFromDuplicates()
        self.assertTrue(
            subscriber not in duplicate_subscribers,
            "Subscriber should not be in duplicate_subscribers.")


class TestBugStructuralSubscribers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_getStructuralSubscribers_no_subscribers(self):
        # If there are no subscribers for any of the bug's targets then no
        # subscribers will be returned by getStructuralSubscribers().
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        subscribers = bug.getStructuralSubscribers()
        self.assertIsInstance(subscribers, ResultSet)
        self.assertEqual([], list(subscribers))

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

        subscribers = bug.getStructuralSubscribers()
        self.assertIsInstance(subscribers, ResultSet)
        self.assertEqual(set([subscriber1, subscriber2]), set(subscribers))

    def test_getStructuralSubscribers_recipients(self):
        # If provided, getStructuralSubscribers() calls the appropriate
        # methods on a BugNotificationRecipients object.
        subscriber = self.factory.makePerson()
        login_person(subscriber)
        product = self.factory.makeProduct()
        product.addBugSubscription(subscriber, subscriber)
        bug = self.factory.makeBug(product=product)
        recipients = BugNotificationRecipients()
        subscribers = bug.getStructuralSubscribers(recipients=recipients)
        # The return value is a list only when populating recipients.
        self.assertIsInstance(subscribers, list)
        self.assertEqual([subscriber], recipients.getRecipients())
        reason, header = recipients.getReason(subscriber)
        self.assertThat(
            reason, StartsWith(
                u"You received this bug notification because "
                u"you are subscribed to "))
        self.assertThat(header, StartsWith(u"Subscriber "))

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
