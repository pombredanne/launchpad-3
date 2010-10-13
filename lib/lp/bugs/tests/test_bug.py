# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
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
        team1 = self.factory.makeTeam(members=[person])
        team2 = self.factory.makeTeam(members=[person])
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
        # getDirectSubscribers(). If passed, getDirectSubscribers() will
        # return only those subscribers who will receive that level of
        # notifications or higher.
        bug = self.factory.makeBug()
        # We unsubscribe the bug's owner because if we don't there will
        # be two COMMENTS-level subscribers.
        with person_logged_in(bug.owner):
            bug.unsubscribe(bug.owner, bug.owner)
        for level in BugNotificationLevel.items:
            subscriber = self.factory.makePerson()
            with person_logged_in(subscriber):
                subscription = bug.subscribe(
                    subscriber, subscriber, level=level)
            direct_subscribers = bug.getDirectSubscribers(level=level)
            self.assertTrue(
                subscriber in direct_subscribers,
                "Subscriber at level %s is not in direct_subscribers." %
                level.name)
            self.assertEqual(
                1, len(direct_subscribers),
                "There should be only one direct subscriber for level %s." %
                level.name)

    def test_get_direct_subscribers_default_level(self):
        # If no `level` parameter is passed to getDirectSubscribers(),
        # the assumed `level` is BugNotification.COMMENTS.
        bug = self.factory.makeBug()
        level = BugNotificationLevel.COMMENTS
        subscriber = self.factory.makePerson()
        with person_logged_in(subscriber):
            subscription = bug.subscribe(
                subscriber, subscriber, level=level)
        direct_subscribers = bug.getDirectSubscribers(level=level)
        self.assertTrue(
            bug.owner in direct_subscribers,
            "Bug owner is not in direct_subscribers to COMMENTS.")
        self.assertTrue(
            subscriber in direct_subscribers,
            "Subscriber at level COMMENTS is not in direct_subscribers.")
        self.assertEqual(
            2, len(direct_subscribers),
            "There should be two direct subscribers to COMMENTS.")

    def test_subscribers_from_dupes_uses_level(self):
        # When getSubscribersFromDuplicates() is passed a `level`
        # parameter it will include only subscribers subscribed to
        # duplicates at that BugNotificationLevel.
        bug = self.factory.makeBug()
        duplicate_bug = self.factory.makeBug()
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(bug)
            # We unsubscribe the owner of the duplicate to avoid muddling
            # the results retuned by getSubscribersFromDuplicates()
            duplicate_bug.unsubscribe(
                duplicate_bug.owner, duplicate_bug.owner)
        for level in BugNotificationLevel.items:
            subscriber = self.factory.makePerson()
            with person_logged_in(subscriber):
                subscription = duplicate_bug.subscribe(
                    subscriber, subscriber, level=level)
            duplicate_subscribers = (
                bug.getSubscribersFromDuplicates(level=level))
            self.assertTrue(
                subscriber in duplicate_subscribers,
                "Subscriber at level %s is not in duplicate_subscribers." %
                level.name)
            self.assertEqual(
                1, len(duplicate_subscribers),
                "There should be only one subscriber to the duplicate "
                "for level %s." % level.name)

    def test_subscribers_from_dupes_overrides_using_level(self):
        # Bug.getSubscribersFromDuplicates() does not return subscribers
        # who also have a direct subscription to the master bug. This
        # happens regardless of the level argument passed to
        # getSubscribersFromDuplicates().
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
                subscriber, subscriber, level=BugNotificationLevel.METADATA)
            dupe_subscription = duplicate_bug.subscribe(
                subscriber, subscriber, level=BugNotificationLevel.NOTHING)
        duplicate_subscribers = bug.getSubscribersFromDuplicates()
        self.assertTrue(
            subscriber not in duplicate_subscribers,
            "Subscriber should not be in duplicate_subscribers.")
