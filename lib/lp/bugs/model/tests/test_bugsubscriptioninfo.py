# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test `BugSubscriptionInfo`."""

__metaclass__ = type

from contextlib import contextmanager

from storm.store import Store
from testtools.matchers import Equals
from zope.component import queryAdapter
from zope.security.checker import getChecker

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.interfaces.security import IAuthorization
from lp.bugs.enum import BugNotificationLevel
from lp.bugs.model.bug import (
    BugSubscriberSet,
    BugSubscriptionInfo,
    BugSubscriptionSet,
    load_people,
    StructuralSubscriptionSet,
    )
from lp.bugs.security import (
    PublicToAllOrPrivateToExplicitSubscribersForBugTask,
    )
from lp.registry.model.person import Person
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.matchers import HasQueryCount


class TestLoadPeople(TestCaseWithFactory):
    """Tests for `load_people`."""

    layer = DatabaseFunctionalLayer

    def test(self):
        expected = [
            self.factory.makePerson(),
            self.factory.makeTeam(),
            ]
        observed = load_people(
            Person.id.is_in(person.id for person in expected))
        self.assertEqual(set(expected), set(observed))


class TestSubscriptionRelatedSets(TestCaseWithFactory):
    """Tests for *Set classes related to subscriptions."""

    layer = DatabaseFunctionalLayer

    name_pairs = ("A", "xa"), ("C", "xd"), ("B", "xb"), ("C", "xc")
    name_pairs_sorted = ("A", "xa"), ("B", "xb"), ("C", "xc"), ("C", "xd")

    def setUp(self):
        super(TestSubscriptionRelatedSets, self).setUp()
        make_person = lambda (displayname, name): (
            self.factory.makePerson(displayname=displayname, name=name))
        subscribers = dict(
            (name_pair, make_person(name_pair))
            for name_pair in self.name_pairs)
        self.subscribers_set = frozenset(subscribers.itervalues())
        self.subscribers_sorted = tuple(
            subscribers[name_pair] for name_pair in self.name_pairs_sorted)

    def test_BugSubscriberSet(self):
        subscriber_set = BugSubscriberSet(self.subscribers_set)
        self.assertIsInstance(subscriber_set, frozenset)
        self.assertEqual(self.subscribers_set, subscriber_set)
        self.assertEqual(self.subscribers_sorted, subscriber_set.sorted)

    def test_BugSubscriptionSet(self):
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            subscriptions = frozenset(
                bug.subscribe(subscriber, subscriber)
                for subscriber in self.subscribers_set)
        subscription_set = BugSubscriptionSet(subscriptions)
        self.assertIsInstance(subscription_set, frozenset)
        self.assertEqual(subscriptions, subscription_set)
        # BugSubscriptionSet.sorted returns a tuple of subscriptions ordered
        # by subscribers.
        self.assertEqual(
            self.subscribers_sorted, tuple(
                subscription.person
                for subscription in subscription_set.sorted))
        # BugSubscriptionSet.subscribers returns a BugSubscriberSet of the
        # subscription's subscribers.
        self.assertIsInstance(subscription_set.subscribers, BugSubscriberSet)
        self.assertEqual(self.subscribers_set, subscription_set.subscribers)

    def test_StructuralSubscriptionSet(self):
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            subscriptions = frozenset(
                product.addSubscription(subscriber, subscriber)
                for subscriber in self.subscribers_set)
        subscription_set = StructuralSubscriptionSet(subscriptions)
        self.assertIsInstance(subscription_set, frozenset)
        self.assertEqual(subscriptions, subscription_set)
        # StructuralSubscriptionSet.sorted returns a tuple of subscriptions
        # ordered by subscribers.
        self.assertEqual(
            self.subscribers_sorted, tuple(
                subscription.subscriber
                for subscription in subscription_set.sorted))
        # StructuralSubscriptionSet.subscribers returns a BugSubscriberSet of
        # the subscription's subscribers.
        self.assertIsInstance(subscription_set.subscribers, BugSubscriberSet)
        self.assertEqual(self.subscribers_set, subscription_set.subscribers)


class TestBugSubscriptionInfo(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionInfo, self).setUp()
        self.target = self.factory.makeProduct(
            bug_supervisor=self.factory.makePerson())
        self.bug = self.factory.makeBug(product=self.target)
        # Unsubscribe the bug filer to make the tests more readable.
        with person_logged_in(self.bug.owner):
            self.bug.unsubscribe(self.bug.owner, self.bug.owner)

    def getInfo(self):
        return BugSubscriptionInfo(
            self.bug, BugNotificationLevel.LIFECYCLE)

    def _create_direct_subscriptions(self):
        subscribers = (
            self.factory.makePerson(),
            self.factory.makePerson())
        with person_logged_in(self.bug.owner):
            subscriptions = tuple(
                self.bug.subscribe(subscriber, subscriber)
                for subscriber in subscribers)
        return subscribers, subscriptions

    def test_direct(self):
        # The set of direct subscribers.
        subscribers, subscriptions = self._create_direct_subscriptions()
        found_subscriptions = self.getInfo().direct_subscriptions
        self.assertEqual(set(subscriptions), found_subscriptions)
        self.assertEqual(subscriptions, found_subscriptions.sorted)
        self.assertEqual(set(subscribers), found_subscriptions.subscribers)
        self.assertEqual(subscribers, found_subscriptions.subscribers.sorted)

    def test_muted_direct(self):
        # If a direct is muted, it is not listed.
        subscribers, subscriptions = self._create_direct_subscriptions()
        with person_logged_in(subscribers[0]):
            self.bug.mute(subscribers[0], subscribers[0])
        found_subscriptions = self.getInfo().direct_subscriptions
        self.assertEqual(set([subscriptions[1]]), found_subscriptions)

    def _create_duplicate_subscription(self):
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)
            duplicate_bug_subscription = (
                duplicate_bug.getSubscriptionForPerson(
                    duplicate_bug.owner))
        return duplicate_bug, duplicate_bug_subscription

    def test_duplicate(self):
        # The set of subscribers from duplicate bugs.
        found_subscriptions = self.getInfo().duplicate_subscriptions
        self.assertEqual(set(), found_subscriptions)
        self.assertEqual((), found_subscriptions.sorted)
        self.assertEqual(set(), found_subscriptions.subscribers)
        self.assertEqual((), found_subscriptions.subscribers.sorted)
        duplicate_bug, duplicate_bug_subscription = (
            self._create_duplicate_subscription())
        found_subscriptions = self.getInfo().duplicate_subscriptions
        self.assertEqual(
            set([duplicate_bug_subscription]),
            found_subscriptions)
        self.assertEqual(
            (duplicate_bug_subscription,),
            found_subscriptions.sorted)
        self.assertEqual(
            set([duplicate_bug.owner]),
            found_subscriptions.subscribers)
        self.assertEqual(
            (duplicate_bug.owner,),
            found_subscriptions.subscribers.sorted)

    def test_muted_duplicate(self):
        # If a duplicate is muted, it is not listed.
        duplicate_bug, duplicate_bug_subscription = (
            self._create_duplicate_subscription())
        with person_logged_in(duplicate_bug.owner):
            self.bug.mute(duplicate_bug.owner, duplicate_bug.owner)
        found_subscriptions = self.getInfo().duplicate_subscriptions
        self.assertEqual(set(), found_subscriptions)

    def test_duplicate_for_private_bug(self):
        # The set of subscribers from duplicate bugs is always empty when the
        # master bug is private.
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)
        with person_logged_in(self.bug.owner):
            self.bug.setPrivate(True, self.bug.owner)
        found_subscriptions = self.getInfo().duplicate_subscriptions
        self.assertEqual(set(), found_subscriptions)
        self.assertEqual((), found_subscriptions.sorted)
        self.assertEqual(set(), found_subscriptions.subscribers)
        self.assertEqual((), found_subscriptions.subscribers.sorted)

    def test_duplicate_only(self):
        # The set of duplicate subscriptions where the subscriber has no other
        # subscriptions.
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)
            duplicate_bug_subscription = (
                duplicate_bug.getSubscriptionForPerson(
                    duplicate_bug.owner))
        found_subscriptions = self.getInfo().duplicate_only_subscriptions
        self.assertEqual(
            set([duplicate_bug_subscription]),
            found_subscriptions)
        # If a user is subscribed to a duplicate bug and is a bugtask
        # assignee, for example, their duplicate subscription will not be
        # included.
        with person_logged_in(self.target.owner):
            self.bug.default_bugtask.transitionToAssignee(
                duplicate_bug_subscription.person)
        found_subscriptions = self.getInfo().duplicate_only_subscriptions
        self.assertEqual(set(), found_subscriptions)

    def test_structural(self):
        # The set of structural subscribers.
        subscribers = (
            self.factory.makePerson(),
            self.factory.makePerson())
        with person_logged_in(self.bug.owner):
            subscriptions = tuple(
                self.target.addBugSubscription(subscriber, subscriber)
                for subscriber in subscribers)
        found_subscriptions = self.getInfo().structural_subscriptions
        self.assertEqual(set(subscriptions), found_subscriptions)
        self.assertEqual(subscriptions, found_subscriptions.sorted)
        self.assertEqual(set(subscribers), found_subscriptions.subscribers)
        self.assertEqual(subscribers, found_subscriptions.subscribers.sorted)

    def test_all_assignees(self):
        # The set of bugtask assignees for bugtasks that have been assigned.
        found_assignees = self.getInfo().all_assignees
        self.assertEqual(set(), found_assignees)
        self.assertEqual((), found_assignees.sorted)
        bugtask = self.bug.default_bugtask
        with person_logged_in(bugtask.pillar.bug_supervisor):
            bugtask.transitionToAssignee(self.bug.owner)
        found_assignees = self.getInfo().all_assignees
        self.assertEqual(set([self.bug.owner]), found_assignees)
        self.assertEqual((self.bug.owner,), found_assignees.sorted)
        bugtask2 = self.factory.makeBugTask(bug=self.bug)
        with person_logged_in(bugtask2.pillar.owner):
            bugtask2.transitionToAssignee(bugtask2.owner)
        found_assignees = self.getInfo().all_assignees
        self.assertEqual(
            set([self.bug.owner, bugtask2.owner]),
            found_assignees)
        self.assertEqual(
            (self.bug.owner, bugtask2.owner),
            found_assignees.sorted)

    def test_all_pillar_owners_without_bug_supervisors(self):
        # The set of owners of pillars for which no bug supervisor is
        # configured.
        [bugtask] = self.bug.bugtasks
        found_owners = (
            self.getInfo().all_pillar_owners_without_bug_supervisors)
        self.assertEqual(set(), found_owners)
        self.assertEqual((), found_owners.sorted)
        # Clear the supervisor for the first bugtask's target.
        with person_logged_in(bugtask.target.owner):
            bugtask.target.setBugSupervisor(None, bugtask.owner)
        found_owners = (
            self.getInfo().all_pillar_owners_without_bug_supervisors)
        self.assertEqual(set([bugtask.pillar.owner]), found_owners)
        self.assertEqual((bugtask.pillar.owner,), found_owners.sorted)
        # Add another bugtask with a bug supervisor.
        target2 = self.factory.makeProduct(bug_supervisor=None)
        bugtask2 = self.factory.makeBugTask(bug=self.bug, target=target2)
        found_owners = (
            self.getInfo().all_pillar_owners_without_bug_supervisors)
        self.assertEqual(
            set([bugtask.pillar.owner, bugtask2.pillar.owner]),
            found_owners)
        self.assertEqual(
            (bugtask.pillar.owner, bugtask2.pillar.owner),
            found_owners.sorted)

    def _create_also_notified_subscribers(self):
        # Add an assignee, a bug supervisor and a structural subscriber.
        bugtask = self.bug.default_bugtask
        assignee = self.factory.makePerson()
        with person_logged_in(bugtask.pillar.bug_supervisor):
            bugtask.transitionToAssignee(assignee)
        supervisor = self.factory.makePerson()
        with person_logged_in(bugtask.target.owner):
            bugtask.target.setBugSupervisor(supervisor, supervisor)
        structural_subscriber = self.factory.makePerson()
        with person_logged_in(structural_subscriber):
            bugtask.target.addSubscription(
                structural_subscriber, structural_subscriber)
        return assignee, supervisor, structural_subscriber

    def test_also_notified_subscribers(self):
        # The set of also notified subscribers.
        found_subscribers = self.getInfo().also_notified_subscribers
        self.assertEqual(set(), found_subscribers)
        self.assertEqual((), found_subscribers.sorted)
        assignee, supervisor, structural_subscriber = (
            self._create_also_notified_subscribers())
        # Add a direct subscription.
        direct_subscriber = self.factory.makePerson()
        with person_logged_in(self.bug.owner):
            self.bug.subscribe(direct_subscriber, direct_subscriber)
        # The direct subscriber does not appear in the also notified set, but
        # the assignee, supervisor and structural subscriber do.
        found_subscribers = self.getInfo().also_notified_subscribers
        self.assertEqual(
            set([assignee, supervisor, structural_subscriber]),
            found_subscribers)
        self.assertEqual(
            (assignee, supervisor, structural_subscriber),
            found_subscribers.sorted)

    def test_muted_also_notified_subscribers(self):
        # If someone is muted, they are not listed in the
        # also_notified_subscribers.
        assignee, supervisor, structural_subscriber = (
            self._create_also_notified_subscribers())
        # As a control, we first show that the
        # the assignee, supervisor and structural subscriber do show up
        # when they are not muted.
        found_subscribers = self.getInfo().also_notified_subscribers
        self.assertEqual(
            set([assignee, supervisor, structural_subscriber]),
            found_subscribers)
        # Now we mute all of the subscribers.
        with person_logged_in(assignee):
            self.bug.mute(assignee, assignee)
        with person_logged_in(supervisor):
            self.bug.mute(supervisor, supervisor)
        with person_logged_in(structural_subscriber):
            self.bug.mute(structural_subscriber, structural_subscriber)
        # Now we don't see them.
        found_subscribers = self.getInfo().also_notified_subscribers
        self.assertEqual(
            set(), found_subscribers)

    def test_also_notified_subscribers_for_private_bug(self):
        # The set of also notified subscribers is always empty when the master
        # bug is private.
        assignee = self.factory.makePerson()
        bugtask = self.bug.default_bugtask
        with person_logged_in(bugtask.pillar.bug_supervisor):
            bugtask.transitionToAssignee(assignee)
        with person_logged_in(self.bug.owner):
            self.bug.setPrivate(True, self.bug.owner)
        found_subscribers = self.getInfo().also_notified_subscribers
        self.assertEqual(set(), found_subscribers)
        self.assertEqual((), found_subscribers.sorted)

    def test_indirect_subscribers(self):
        # The set of indirect subscribers is the union of also notified
        # subscribers and subscribers to duplicates.
        assignee = self.factory.makePerson()
        bugtask = self.bug.default_bugtask
        with person_logged_in(bugtask.pillar.bug_supervisor):
            bugtask.transitionToAssignee(assignee)
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)
        found_subscribers = self.getInfo().indirect_subscribers
        self.assertEqual(
            set([assignee, duplicate_bug.owner]),
            found_subscribers)
        self.assertEqual(
            (assignee, duplicate_bug.owner),
            found_subscribers.sorted)


class TestBugSubscriptionInfoPermissions(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test(self):
        bug = self.factory.makeBug()
        info = bug.getSubscriptionInfo()
        checker = getChecker(info)

        # BugSubscriptionInfo objects are immutable.
        self.assertEqual({}, checker.set_permissions)

        # All attributes require launchpad.View.
        permissions = set(checker.get_permissions.itervalues())
        self.assertEqual(set(["launchpad.View"]), permissions)

        # The security adapter for launchpad.View lets anyone reference the
        # attributes unless the bug is private, in which case only explicit
        # subscribers are permitted.
        adapter = queryAdapter(info, IAuthorization, "launchpad.View")
        self.assertIsInstance(
            adapter, PublicToAllOrPrivateToExplicitSubscribersForBugTask)


class TestBugSubscriptionInfoQueries(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionInfoQueries, self).setUp()
        self.target = self.factory.makeProduct()
        self.bug = self.factory.makeBug(product=self.target)
        self.info = BugSubscriptionInfo(
            self.bug, BugNotificationLevel.LIFECYCLE)
        # Get the Storm cache into a known state.
        self.store = Store.of(self.bug)
        self.store.invalidate()
        self.store.reload(self.bug)
        self.bug.bugtasks
        self.bug.tags

    @contextmanager
    def exactly_x_queries(self, count):
        # Assert that there are exactly `count` queries sent to the database
        # in this context. Flush first to ensure we don't count things that
        # happened before entering this context.
        self.store.flush()
        condition = HasQueryCount(Equals(count))
        with StormStatementRecorder() as recorder:
            yield recorder
        self.assertThat(recorder, condition)

    def exercise_subscription_set(self, set_name):
        # Looking up subscriptions takes a single query.
        with self.exactly_x_queries(1):
            getattr(self.info, set_name)
        # Getting the subscribers results in one additional query.
        with self.exactly_x_queries(1):
            getattr(self.info, set_name).subscribers
        # Everything is now cached so no more queries are needed.
        with self.exactly_x_queries(0):
            getattr(self.info, set_name).subscribers
            getattr(self.info, set_name).subscribers.sorted

    def exercise_subscription_set_sorted_first(self, set_name):
        # Looking up subscriptions takes a single query.
        with self.exactly_x_queries(1):
            getattr(self.info, set_name)
        # Getting the sorted subscriptions takes one additional query.
        with self.exactly_x_queries(1):
            getattr(self.info, set_name).sorted
        # Everything is now cached so no more queries are needed.
        with self.exactly_x_queries(0):
            getattr(self.info, set_name).subscribers
            getattr(self.info, set_name).subscribers.sorted

    def test_direct_subscriptions(self):
        self.exercise_subscription_set(
            "direct_subscriptions")

    def test_direct_subscriptions_sorted_first(self):
        self.exercise_subscription_set_sorted_first(
            "direct_subscriptions")

    def make_duplicate_bug(self):
        duplicate_bug = self.factory.makeBug(product=self.target)
        with person_logged_in(duplicate_bug.owner):
            duplicate_bug.markAsDuplicate(self.bug)

    def test_duplicate_subscriptions(self):
        self.make_duplicate_bug()
        self.exercise_subscription_set(
            "duplicate_subscriptions")

    def test_duplicate_subscriptions_sorted_first(self):
        self.make_duplicate_bug()
        self.exercise_subscription_set_sorted_first(
            "duplicate_subscriptions")

    def test_duplicate_subscriptions_for_private_bug(self):
        self.make_duplicate_bug()
        with person_logged_in(self.bug.owner):
            self.bug.setPrivate(True, self.bug.owner)
        with self.exactly_x_queries(0):
            self.info.duplicate_subscriptions
        with self.exactly_x_queries(0):
            self.info.duplicate_subscriptions.subscribers

    def add_structural_subscriber(self):
        with person_logged_in(self.bug.owner):
            self.target.addSubscription(self.bug.owner, self.bug.owner)

    def test_structural_subscriptions(self):
        self.add_structural_subscriber()
        self.exercise_subscription_set(
            "structural_subscriptions")

    def test_structural_subscriptions_sorted_first(self):
        self.add_structural_subscriber()
        self.exercise_subscription_set_sorted_first(
            "structural_subscriptions")

    def test_all_assignees(self):
        with self.exactly_x_queries(1):
            self.info.all_assignees

    def test_all_pillar_owners_without_bug_supervisors(self):
        # Getting all bug supervisors and pillar owners can take several
        # queries. However, there are typically few tasks so the trade for
        # simplicity of implementation is acceptable. Only the simplest case
        # is tested here.
        with self.exactly_x_queries(1):
            self.info.all_pillar_owners_without_bug_supervisors

    def test_also_notified_subscribers(self):
        with self.exactly_x_queries(5):
            self.info.also_notified_subscribers

    def test_also_notified_subscribers_later(self):
        # When also_notified_subscribers is referenced after some other sets
        # in BugSubscriptionInfo are referenced, everything comes from cache.
        self.info.all_assignees
        self.info.all_pillar_owners_without_bug_supervisors
        self.info.direct_subscriptions.subscribers
        self.info.structural_subscriptions.subscribers
        with self.exactly_x_queries(1):
            self.info.also_notified_subscribers

    def test_indirect_subscribers(self):
        with self.exactly_x_queries(6):
            self.info.indirect_subscribers

    def test_indirect_subscribers_later(self):
        # When indirect_subscribers is referenced after some other sets in
        # BugSubscriptionInfo are referenced, everything comes from cache.
        self.info.also_notified_subscribers
        self.info.duplicate_subscriptions.subscribers
        with self.exactly_x_queries(0):
            self.info.indirect_subscribers
