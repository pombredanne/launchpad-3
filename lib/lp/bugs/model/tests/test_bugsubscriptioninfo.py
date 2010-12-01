# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `BugSubscriptionInfo`."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.model.bug import BugSubscriptionInfo
from lp.registry.enum import BugNotificationLevel
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount
from testtools.matchers import Equals
from storm.store import Store


class TestBugSubscriptionInfo(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionInfo, self).setUp()
        self.target = self.factory.makeProduct()
        self.bug = self.factory.makeBug(product=self.target)
        # Unsubscribe the bug filer to make the tests more readable.
        with person_logged_in(self.bug.owner):
            self.bug.unsubscribe(self.bug.owner, self.bug.owner)
        self.info = BugSubscriptionInfo(
            self.bug, BugNotificationLevel.NOTHING)

    def test_direct(self):
        # The set of direct subscribers.
        subscribers = set(
            [self.factory.makePerson(), self.factory.makePerson()])
        with person_logged_in(self.bug.owner):
            subscriptions = set(
                self.bug.subscribe(subscriber, subscriber)
                for subscriber in subscribers)
        self.assertEqual(subscribers, self.info.direct_subscribers)
        self.assertEqual(subscriptions, self.info.direct_subscriptions)

    def test_duplicate(self):
        # The set of subscribers from duplicate bugs.
        self.assertEqual(set(), self.info.duplicate_subscribers)
        self.assertEqual(set(), self.info.duplicate_subscriptions)
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)
        self.assertEqual(
            set([duplicate_bug.owner]),
            self.info.duplicate_subscribers)
        self.assertEqual(
            set([duplicate_bug.getSubscriptionForPerson(
                        duplicate_bug.owner)]),
            self.info.duplicate_subscriptions)

    def test_duplicate_for_private_bug(self):
        # The set of subscribers from duplicate bugs is always empty when the
        # master bug is private.
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)
        with person_logged_in(self.bug.owner):
            self.bug.setPrivate(True, self.bug.owner)
        self.assertEqual(set(), self.info.duplicate_subscribers)
        self.assertEqual(set(), self.info.duplicate_subscriptions)

    def test_structural(self):
        # The set of structural subscribers.
        subscribers = set(
            [self.factory.makePerson(), self.factory.makePerson()])
        with person_logged_in(self.bug.owner):
            subscriptions = set(
                self.target.addBugSubscription(subscriber, subscriber)
                for subscriber in subscribers)
        self.assertEqual(subscribers, self.info.structural_subscribers)
        self.assertEqual(subscriptions, self.info.structural_subscriptions)

    def test_all_assignees(self):
        # The set of bugtask assignees for bugtasks that have been assigned.
        self.assertEqual(set(), self.info.all_assignees)
        with person_logged_in(self.bug.owner):
            self.bug.default_bugtask.transitionToAssignee(self.bug.owner)
        self.assertEqual(set([self.bug.owner]), self.info.all_assignees)
        bugtask = self.factory.makeBugTask(bug=self.bug)
        with person_logged_in(bugtask.owner):
            bugtask.transitionToAssignee(bugtask.owner)
        self.assertEqual(
            set([self.bug.owner, bugtask.owner]),
            self.info.all_assignees)

    def test_all_bug_supervisors(self):
        # The set of bug supervisors for the bug's task's target, where
        # supervisors have been configured.
        self.assertEqual(set(), self.info.all_bug_supervisors)
        # Set the supervisor for the first bugtask's target.
        [bugtask] = self.bug.bugtasks
        with person_logged_in(bugtask.target.owner):
            bugtask.target.setBugSupervisor(
                bugtask.owner, bugtask.owner)
        self.assertEqual(
            set([bugtask.owner]),
            self.info.all_bug_supervisors)
        # Add another bugtask and set its target's supervisor too.
        bugtask2 = self.factory.makeBugTask(bug=self.bug)
        with person_logged_in(bugtask2.target.owner):
            bugtask2.target.setBugSupervisor(
                bugtask2.owner, bugtask2.owner)
        self.assertEqual(
            set([bugtask.owner, bugtask2.owner]),
            self.info.all_bug_supervisors)

    def test_also_notified_subscribers(self):
        # The set of also notified subscribers.
        self.assertEqual(set(), self.info.also_notified_subscribers)
        # Add an assignee, a bug supervisor and a structural subscriber.
        bugtask = self.bug.default_bugtask
        assignee = self.factory.makePerson()
        with person_logged_in(self.bug.owner):
            bugtask.transitionToAssignee(assignee)
        supervisor = self.factory.makePerson()
        with person_logged_in(bugtask.target.owner):
            bugtask.target.setBugSupervisor(supervisor, supervisor)
        structural_subscriber = self.factory.makePerson()
        with person_logged_in(structural_subscriber):
            bugtask.target.addSubscription(
                structural_subscriber, structural_subscriber)
        # Add a direct subscription.
        direct_subscriber = self.factory.makePerson()
        with person_logged_in(self.bug.owner):
            self.bug.subscribe(direct_subscriber, direct_subscriber)
        # The direct subscriber does not appear in the also notified set, but
        # the assignee, supervisor and structural subscriber do.
        self.assertEqual(
            set([assignee, supervisor, structural_subscriber]),
            self.info.also_notified_subscribers)

    def test_also_notified_subscribers_for_private_bug(self):
        # The set of also notified subscribers is always empty when the master
        # bug is private.
        assignee = self.factory.makePerson()
        with person_logged_in(self.bug.owner):
            self.bug.default_bugtask.transitionToAssignee(assignee)
        with person_logged_in(self.bug.owner):
            self.bug.setPrivate(True, self.bug.owner)
        self.assertEqual(set(), self.info.also_notified_subscribers)

    def test_indirect_subscribers(self):
        # The set of indirect subscribers is the union of also notified
        # subscribers and subscribers to duplicates.
        assignee = self.factory.makePerson()
        with person_logged_in(self.bug.owner):
            self.bug.default_bugtask.transitionToAssignee(assignee)
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)
        self.assertEqual(
            set([assignee, duplicate_bug.owner]),
            self.info.indirect_subscribers)


class TestBugSubscriptionInfoQueries(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionInfoQueries, self).setUp()
        self.target = self.factory.makeProduct()
        self.bug = self.factory.makeBug(product=self.target)
        self.info = BugSubscriptionInfo(
            self.bug, BugNotificationLevel.NOTHING)
        # Get the Storm cache into a known state.
        Store.of(self.bug).invalidate()
        Store.of(self.bug).reload(self.bug)
        self.bug.bugtasks
        self.bug.tags

    def test_direct_subscribers(self):
        # Looking up subscribers takes two queries: one to obtain
        # subscriptions and another to load the Person records.
        with StormStatementRecorder() as recorder:
            self.info.direct_subscribers
        self.assertThat(recorder, HasQueryCount(Equals(2)))

    def test_direct_subscriptions(self):
        # Looking up subscriptions takes a single query.
        with StormStatementRecorder() as recorder:
            self.info.direct_subscriptions
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_duplicate_subscribers(self):
        # Looking up duplicate subscribers takes two queries: one to obtain
        # subscriptions and another to load the Person records.
        with StormStatementRecorder() as recorder:
            self.info.duplicate_subscribers
        self.assertThat(recorder, HasQueryCount(Equals(2)))

    def test_duplicate_subscriptions(self):
        # Looking up duplicate subscriptions takes a single query.
        with StormStatementRecorder() as recorder:
            self.info.duplicate_subscriptions
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_duplicate_subscribers_for_private_bug(self):
        # Looking up duplicate subscribers for a private bug takes a single
        # query; obtaining subscriptions is short-circuited.
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)
        with person_logged_in(self.bug.owner):
            self.bug.setPrivate(True, self.bug.owner)
        with StormStatementRecorder() as recorder:
            self.info.duplicate_subscribers
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_duplicate_subscriptions_for_private_bug(self):
        # Looking up duplicate subscriptions for a private bug is
        # short-circuited.
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)
        with person_logged_in(self.bug.owner):
            self.bug.setPrivate(True, self.bug.owner)
        with StormStatementRecorder() as recorder:
            self.info.duplicate_subscriptions
        self.assertThat(recorder, HasQueryCount(Equals(0)))

    def test_structural_subscribers(self):
        # Looking up structural subscribers takes three queries: one to obtain
        # subscriptions and another to load the Person records.
        with StormStatementRecorder() as recorder:
            self.info.structural_subscribers
        self.assertThat(recorder, HasQueryCount(Equals(2)))

    def test_structural_subscriptions(self):
        # Looking up structural subscriptions takes a single query.
        with StormStatementRecorder() as recorder:
            self.info.structural_subscriptions
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_all_assignees(self):
        # Getting all assignees takes a single query.
        with StormStatementRecorder() as recorder:
            self.info.all_assignees
        self.assertThat(recorder, HasQueryCount(Equals(1)))

    def test_all_bug_supervisors(self):
        # Getting all bug supervisors can take several queries; bugtask
        # pillars need to be loaded, then supervisors need to be
        # loaded. However, there are typically few tasks so the trade for
        # simplicity of implementation is acceptable. Only the simplest case
        # is tested here: no queries are needed when there's a single bugtask
        # and its target does not have a bug supervisor (presumably because
        # the pillar is already cached).
        with StormStatementRecorder() as recorder:
            self.info.all_bug_supervisors
        self.assertThat(recorder, HasQueryCount(Equals(0)))

    def test_also_notified_subscribers(self):
        # Looking up also notified subscribers requires 5 queries.
        with StormStatementRecorder() as recorder:
            self.info.also_notified_subscribers
        self.assertThat(recorder, HasQueryCount(Equals(5)))

    def test_indirect_subscribers(self):
        # Looking up indirect subscribers requires 7 queries.
        with StormStatementRecorder() as recorder:
            self.info.indirect_subscribers
        self.assertThat(recorder, HasQueryCount(Equals(7)))
