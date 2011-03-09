# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `StructuralSubscription`."""

__metaclass__ = type

from storm.store import (
    EmptyResultSet,
    ResultSet,
    Store,
    )
from testtools.matchers import StartsWith
from zope.security.interfaces import Unauthorized

from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    DatabaseFunctionalLayer,
    )
from lp.bugs.enum import BugNotificationLevel
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.mail.bugnotificationrecipients import BugNotificationRecipients
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.model.structuralsubscription import (
    get_all_structural_subscriptions,
    get_structural_subscribers,
    get_structural_subscription_targets,
    )
from lp.testing import (
    anonymous_logged_in,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )


class TestStructuralSubscription(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscription, self).setUp()
        self.product = self.factory.makeProduct()
        with person_logged_in(self.product.owner):
            self.subscription = self.product.addSubscription(
                self.product.owner, self.product.owner)
        self.original_filter = self.subscription.bug_filters[0]

    def test_delete_requires_Edit_permission(self):
        # delete() is only available to the subscriber.
        # We use a lambda here because a security proxy around
        # self.subscription is giving us the behavior we want to
        # demonstrate.  Merely accessing the "delete" name raises
        # Unauthorized, before the method is even called.  Therefore,
        # we use a lambda to make the trigger happen within "assertRaises".
        with anonymous_logged_in():
            self.assertRaises(Unauthorized, lambda: self.subscription.delete)
        with person_logged_in(self.factory.makePerson()):
            self.assertRaises(Unauthorized, lambda: self.subscription.delete)

    def test_simple_delete(self):
        with person_logged_in(self.product.owner):
            self.subscription.delete()
            self.assertEqual(
                self.product.getSubscription(self.product.owner), None)

    def test_delete_cascades_to_filters(self):
        with person_logged_in(self.product.owner):
            subscription_id = self.subscription.id
            self.subscription.newBugFilter()
            self.subscription.delete()
            self.assertEqual(
                self.product.getSubscription(self.product.owner), None)
            store = Store.of(self.product)
            # We know that the filter is gone, because we know the
            # subscription is gone, and the database would have
            # prevented the deletion of a subscription without first
            # deleting the filters.  We'll double-check, to be sure.
            self.assertEqual(
                store.find(
                    BugSubscriptionFilter,
                    BugSubscriptionFilter.structural_subscription_id ==
                        subscription_id).one(),
                None)

    def test_bug_filters_default(self):
        # The bug_filters attribute has a default non-filtering bug filter
        # to begin with.
        self.assertEqual([self.original_filter],
                         list(self.subscription.bug_filters))

    def test_bug_filters(self):
        # The bug_filters attribute returns the BugSubscriptionFilter records
        # associated with this subscription.
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structural_subscription = self.subscription
        self.assertContentEqual(
            [subscription_filter, self.original_filter],
            list(self.subscription.bug_filters))

    def test_newBugFilter(self):
        # newBugFilter() creates a new subscription filter linked to the
        # subscription.
        with person_logged_in(self.product.owner):
            subscription_filter = self.subscription.newBugFilter()
        self.assertEqual(
            self.subscription,
            subscription_filter.structural_subscription)
        self.assertContentEqual(
            [subscription_filter, self.original_filter],
            list(self.subscription.bug_filters))

    def test_newBugFilter_by_anonymous(self):
        # newBugFilter() is not available to anonymous users.
        with anonymous_logged_in():
            self.assertRaises(
                Unauthorized, lambda: self.subscription.newBugFilter)

    def test_newBugFilter_by_other_user(self):
        # newBugFilter() is only available to the subscriber.
        with person_logged_in(self.factory.makePerson()):
            self.assertRaises(
                Unauthorized, lambda: self.subscription.newBugFilter)


class FilteredStructuralSubscriptionTestBase:
    """Tests for filtered structural subscriptions."""

    layer = LaunchpadFunctionalLayer

    def makeTarget(self):
        raise NotImplementedError(self.makeTarget)

    def makeBugTask(self):
        return self.factory.makeBugTask(target=self.target)

    def setUp(self):
        super(FilteredStructuralSubscriptionTestBase, self).setUp()
        self.ordinary_subscriber = self.factory.makePerson()
        login_person(self.ordinary_subscriber)
        self.target = self.makeTarget()
        self.bugtask = self.makeBugTask()
        self.bug = self.bugtask.bug
        self.subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        self.initial_filter = self.subscription.bug_filters[0]

    def assertSubscribers(
        self, expected_subscribers, level=BugNotificationLevel.NOTHING):
        observed_subscribers = list(
            get_structural_subscribers(self.bugtask, None, level))
        self.assertEqual(expected_subscribers, observed_subscribers)

    def test_getStructuralSubscribers(self):
        # If no one has a filtered subscription for the given bug, the result
        # of get_structural_subscribers() is the same as for
        # the set of people from each subscription in getSubscriptions().
        subscriptions = self.target.getSubscriptions()
        self.assertSubscribers([sub.subscriber for sub in subscriptions])

    def test_getStructuralSubscribers_with_filter_on_status(self):
        # If a status filter exists for a subscription, the result of
        # get_structural_subscribers() may be a subset of getSubscriptions().

        # Without any filters the subscription is found.
        self.assertSubscribers([self.ordinary_subscriber])

        # Filter the subscription to bugs in the CONFIRMED state.
        self.initial_filter.statuses = [BugTaskStatus.CONFIRMED]

        # With the filter the subscription is not found.
        self.assertSubscribers([])

        # If the filter is adjusted, the subscription is found again.
        self.initial_filter.statuses = [self.bugtask.status]
        self.assertSubscribers([self.ordinary_subscriber])

    def test_getStructuralSubscribers_with_filter_on_importance(self):
        # If an importance filter exists for a subscription, the result of
        # get_structural_subscribers() may be a subset of getSubscriptions().

        # Without any filters the subscription is found.
        self.assertSubscribers([self.ordinary_subscriber])

        # Filter the subscription to bugs in the CRITICAL state.
        self.initial_filter.importances = [BugTaskImportance.CRITICAL]

        # With the filter the subscription is not found.
        self.assertSubscribers([])

        # If the filter is adjusted, the subscription is found again.
        self.initial_filter.importances = [self.bugtask.importance]
        self.assertSubscribers([self.ordinary_subscriber])

    def test_getStructuralSubscribers_with_filter_on_level(self):
        # All structural subscriptions have a level for bug notifications
        # which get_structural_subscribers() observes.

        # Adjust the subscription level to METADATA.
        self.initial_filter.bug_notification_level = (
            BugNotificationLevel.METADATA)

        # The subscription is found when looking for NOTHING or above.
        self.assertSubscribers(
            [self.ordinary_subscriber], BugNotificationLevel.NOTHING)
        # The subscription is found when looking for METADATA or above.
        self.assertSubscribers(
            [self.ordinary_subscriber], BugNotificationLevel.METADATA)
        # The subscription is not found when looking for COMMENTS or above.
        self.assertSubscribers(
            [], BugNotificationLevel.COMMENTS)

    def test_getStructuralSubscribers_with_filter_include_any_tags(self):
        # If a subscription filter has include_any_tags, a bug with one or
        # more tags is matched.

        self.initial_filter.include_any_tags = True

        # Without any tags the subscription is not found.
        self.assertSubscribers([])

        # With any tag the subscription is found.
        self.bug.tags = ["foo"]
        self.assertSubscribers([self.ordinary_subscriber])

    def test_getStructuralSubscribers_with_filter_exclude_any_tags(self):
        # If a subscription filter has exclude_any_tags, only bugs with no
        # tags are matched.

        self.initial_filter.exclude_any_tags = True

        # Without any tags the subscription is found.
        self.assertSubscribers([self.ordinary_subscriber])

        # With any tag the subscription is not found.
        self.bug.tags = ["foo"]
        self.assertSubscribers([])

    def test_getStructuralSubscribers_with_filter_for_any_tag(self):
        # If a subscription filter specifies that any of one or more specific
        # tags must be present, bugs with any of those tags are matched.

        # Looking for either the "foo" or the "bar" tag.
        self.initial_filter.tags = [u"foo", u"bar"]
        self.initial_filter.find_all_tags = False

        # Without either tag the subscription is not found.
        self.assertSubscribers([])

        # With either tag the subscription is found.
        self.bug.tags = ["bar", "baz"]
        self.assertSubscribers([self.ordinary_subscriber])

    def test_getStructuralSubscribers_with_filter_for_all_tags(self):
        # If a subscription filter specifies that all of one or more specific
        # tags must be present, bugs with all of those tags are matched.

        # Looking for both the "foo" and the "bar" tag.
        self.initial_filter.tags = [u"foo", u"bar"]
        self.initial_filter.find_all_tags = True

        # Without either tag the subscription is not found.
        self.assertSubscribers([])

        # Without only one of the required tags the subscription is not found.
        self.bug.tags = ["foo"]
        self.assertSubscribers([])

        # With both required tags the subscription is found.
        self.bug.tags = ["foo", "bar"]
        self.assertSubscribers([self.ordinary_subscriber])

    def test_getStructuralSubscribers_with_filter_for_not_any_tag(self):
        # If a subscription filter specifies that any of one or more specific
        # tags must not be present, bugs without any of those tags are
        # matched.

        # Looking to exclude the "foo" or "bar" tags.
        self.initial_filter.tags = [u"-foo", u"-bar"]
        self.initial_filter.find_all_tags = False

        # Without either tag the subscription is found.
        self.assertSubscribers([self.ordinary_subscriber])

        # With both tags, the subscription is omitted.
        self.bug.tags = ["foo", "bar"]
        self.assertSubscribers([])

        # With only one tag, the subscription is found again.
        self.bug.tags = ["foo"]
        self.assertSubscribers([self.ordinary_subscriber])

        # However, if find_all_tags is True, even a single excluded tag
        # causes the subscription to be skipped.
        self.initial_filter.find_all_tags = True
        self.assertSubscribers([])

        # This is also true, of course, if the bug has both tags.
        self.bug.tags = ["foo", "bar"]
        self.assertSubscribers([])

    def test_getStructuralSubscribers_with_filter_for_not_all_tags(self):
        # If a subscription filter specifies that all of one or more specific
        # tags must not be present, bugs without all of those tags are
        # matched.

        # Looking to exclude the "foo" and "bar" tags.
        self.initial_filter.tags = [u"-foo", u"-bar"]
        self.initial_filter.find_all_tags = True

        # Without either tag the subscription is found.
        self.assertSubscribers([self.ordinary_subscriber])

        # With only one of the excluded tags the subscription is not
        # found--we are saying that we want to find both an absence of foo
        # and an absence of bar, and yet foo exists.
        self.bug.tags = ["foo"]
        self.assertSubscribers([])

        # With both tags the subscription is also not found.
        self.bug.tags = ["foo", "bar"]
        self.assertSubscribers([])

    def test_getStructuralSubscribers_with_multiple_filters(self):
        # If multiple filters exist for a subscription, all filters must
        # match.

        # Add the "foo" tag to the bug.
        self.bug.tags = ["foo"]
        self.assertSubscribers([self.ordinary_subscriber])

        # Filter the subscription to bugs in the CRITICAL state.
        self.initial_filter.statuses = [BugTaskStatus.CONFIRMED]
        self.initial_filter.importances = [BugTaskImportance.CRITICAL]

        # With the filter the subscription is not found.
        self.assertSubscribers([])

        # If the filter is adjusted to match status but not importance, the
        # subscription is still not found.
        self.initial_filter.statuses = [self.bugtask.status]
        self.assertSubscribers([])

        # If the filter is adjusted to also match importance, the subscription
        # is found again.
        self.initial_filter.importances = [self.bugtask.importance]
        self.assertSubscribers([self.ordinary_subscriber])

        # If the filter is given some tag criteria, the subscription is not
        # found.
        self.initial_filter.tags = [u"-foo", u"bar", u"baz"]
        self.initial_filter.find_all_tags = False
        self.assertSubscribers([])

        # After removing the "foo" tag and adding the "bar" tag, the
        # subscription is found.
        self.bug.tags = ["bar"]
        self.assertSubscribers([self.ordinary_subscriber])

        # Requiring that all tag criteria are fulfilled causes the
        # subscription to no longer be found.
        self.initial_filter.find_all_tags = True
        self.assertSubscribers([])

        # After adding the "baz" tag, the subscription is found again.
        self.bug.tags = ["bar", "baz"]
        self.assertSubscribers([self.ordinary_subscriber])

    def test_getStructuralSubscribers_any_filter_is_a_match(self):
        # If a subscription has multiple filters, the subscription is selected
        # when any filter is found to match. Put another way, the filters are
        # ORed together.
        subscription_filter1 = self.initial_filter
        subscription_filter1.statuses = [BugTaskStatus.CONFIRMED]
        subscription_filter2 = self.subscription.newBugFilter()
        subscription_filter2.tags = [u"foo"]

        # With the filter the subscription is not found.
        self.assertSubscribers([])

        # If the bugtask is adjusted to match the criteria of the first filter
        # but not those of the second, the subscription is found.
        self.bugtask.transitionToStatus(
            BugTaskStatus.CONFIRMED, self.ordinary_subscriber)
        self.assertSubscribers([self.ordinary_subscriber])

        # If the filter is adjusted to also match the criteria of the second
        # filter, the subscription is still found.
        self.bugtask.bug.tags = [u"foo"]
        self.assertSubscribers([self.ordinary_subscriber])

        # If the bugtask is adjusted to no longer match the criteria of the
        # first filter, the subscription is still found.
        self.bugtask.transitionToStatus(
            BugTaskStatus.INPROGRESS, self.ordinary_subscriber)
        self.assertSubscribers([self.ordinary_subscriber])


class TestStructuralSubscriptionFiltersForDistro(
    FilteredStructuralSubscriptionTestBase, TestCaseWithFactory):

    def makeTarget(self):
        return self.factory.makeDistribution()


class TestStructuralSubscriptionFiltersForProduct(
    FilteredStructuralSubscriptionTestBase, TestCaseWithFactory):

    def makeTarget(self):
        return self.factory.makeProduct()


class TestStructuralSubscriptionFiltersForDistroSourcePackage(
    FilteredStructuralSubscriptionTestBase, TestCaseWithFactory):

    def makeTarget(self):
        return self.factory.makeDistributionSourcePackage()


class TestStructuralSubscriptionFiltersForMilestone(
    FilteredStructuralSubscriptionTestBase, TestCaseWithFactory):

    def makeTarget(self):
        return self.factory.makeMilestone()

    def makeBugTask(self):
        bug = self.factory.makeBug(milestone=self.target)
        return bug.bugtasks[0]


class TestStructuralSubscriptionFiltersForDistroSeries(
    FilteredStructuralSubscriptionTestBase, TestCaseWithFactory):

    def makeTarget(self):
        return self.factory.makeDistroSeries()


class TestStructuralSubscriptionFiltersForProjectGroup(
    FilteredStructuralSubscriptionTestBase, TestCaseWithFactory):

    def makeTarget(self):
        return self.factory.makeProject()

    def makeBugTask(self):
        return self.factory.makeBugTask(
            target=self.factory.makeProduct(project=self.target))


class TestStructuralSubscriptionFiltersForProductSeries(
    FilteredStructuralSubscriptionTestBase, TestCaseWithFactory):

    def makeTarget(self):
        return self.factory.makeProductSeries()


class TestGetStructuralSubscriptionTargets(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_product_target(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        bugtask = bug.bugtasks[0]
        result = get_structural_subscription_targets(bug.bugtasks)
        self.assertEqual(list(result), [(bugtask, product)])

    def test_milestone_target(self):
        actor = self.factory.makePerson()
        login_person(actor)
        product = self.factory.makeProduct()
        milestone = self.factory.makeMilestone(product=product)
        bug = self.factory.makeBug(product=product, milestone=milestone)
        bugtask = bug.bugtasks[0]
        result = get_structural_subscription_targets(bug.bugtasks)
        self.assertEqual(set(result), set(
            ((bugtask, product), (bugtask, milestone))))

    def test_sourcepackage_target(self):
        actor = self.factory.makePerson()
        login_person(actor)
        distroseries = self.factory.makeDistroSeries()
        sourcepackage = self.factory.makeSourcePackage(
            distroseries=distroseries)
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        bug.addTask(actor, sourcepackage)
        product_bugtask = bug.bugtasks[0]
        sourcepackage_bugtask = bug.bugtasks[1]
        result = get_structural_subscription_targets(bug.bugtasks)
        self.assertEqual(set(result), set(
            ((product_bugtask, product),
             (sourcepackage_bugtask, distroseries))))

    def test_distribution_source_package_target(self):
        actor = self.factory.makePerson()
        login_person(actor)
        distribution = self.factory.makeDistribution()
        dist_sourcepackage = self.factory.makeDistributionSourcePackage(
            distribution=distribution)
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        bug.addTask(actor, dist_sourcepackage)
        product_bugtask = bug.bugtasks[0]
        dist_sourcepackage_bugtask = bug.bugtasks[1]
        result = get_structural_subscription_targets(bug.bugtasks)
        self.assertEqual(set(result), set(
            ((product_bugtask, product),
             (dist_sourcepackage_bugtask, dist_sourcepackage),
             (dist_sourcepackage_bugtask, distribution))))


class TestGetAllStructuralSubscriptions(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestGetAllStructuralSubscriptions, self).setUp()
        self.subscriber = self.factory.makePerson()
        login_person(self.subscriber)
        self.product = self.factory.makeProduct()
        self.milestone = self.factory.makeMilestone(product=self.product)
        self.bug = self.factory.makeBug(
            product=self.product, milestone=self.milestone)

    def test_no_subscriptions(self):
        subscriptions = get_all_structural_subscriptions(
            self.bug.bugtasks, self.subscriber)
        self.assertEqual([], list(subscriptions))

    def test_one_subscription(self):
        sub = self.product.addBugSubscription(
            self.subscriber, self.subscriber)
        subscriptions = get_all_structural_subscriptions(
            self.bug.bugtasks, self.subscriber)
        self.assertEqual([sub], list(subscriptions))

    def test_two_subscriptions(self):
        sub1 = self.product.addBugSubscription(
            self.subscriber, self.subscriber)
        sub2 = self.milestone.addBugSubscription(
            self.subscriber, self.subscriber)
        subscriptions = get_all_structural_subscriptions(
            self.bug.bugtasks, self.subscriber)
        self.assertEqual(set([sub1, sub2]), set(subscriptions))

    def test_two_bugtasks_one_subscription(self):
        sub = self.product.addBugSubscription(
            self.subscriber, self.subscriber)
        product2 = self.factory.makeProduct()
        self.bug.addTask(self.subscriber, product2)
        subscriptions = get_all_structural_subscriptions(
            self.bug.bugtasks, self.subscriber)
        self.assertEqual([sub], list(subscriptions))

    def test_two_bugtasks_two_subscriptions(self):
        sub1 = self.product.addBugSubscription(
            self.subscriber, self.subscriber)
        product2 = self.factory.makeProduct()
        self.bug.addTask(self.subscriber, product2)
        sub2 = product2.addBugSubscription(
            self.subscriber, self.subscriber)
        subscriptions = get_all_structural_subscriptions(
            self.bug.bugtasks, self.subscriber)
        self.assertEqual(set([sub1, sub2]), set(subscriptions))

    def test_ignore_other_subscriptions(self):
        sub1 = self.product.addBugSubscription(
            self.subscriber, self.subscriber)
        another_subscriber = self.factory.makePerson()
        login_person(another_subscriber)
        sub2 = self.product.addBugSubscription(
            another_subscriber, another_subscriber)
        subscriptions = get_all_structural_subscriptions(
            self.bug.bugtasks, self.subscriber)
        self.assertEqual([sub1], list(subscriptions))
        subscriptions = get_all_structural_subscriptions(
            self.bug.bugtasks, another_subscriber)
        self.assertEqual([sub2], list(subscriptions))


class TestGetStructuralSubscribers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def make_product_with_bug(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)
        return product, bug

    def test_getStructuralSubscribers_no_subscribers(self):
        # If there are no subscribers for any of the bug's targets then no
        # subscribers will be returned by get_structural_subscribers().
        product, bug = self.make_product_with_bug()
        subscribers = get_structural_subscribers(bug, None, None, None)
        self.assertIsInstance(subscribers, (ResultSet, EmptyResultSet))
        self.assertEqual([], list(subscribers))

    def test_getStructuralSubscribers_single_target(self):
        # Subscribers for any of the bug's targets are returned.
        subscriber = self.factory.makePerson()
        login_person(subscriber)
        product, bug = self.make_product_with_bug()
        product.addBugSubscription(subscriber, subscriber)
        self.assertEqual(
            [subscriber], list(
                get_structural_subscribers(bug, None, None, None)))

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

        subscribers = get_structural_subscribers(bug, None, None, None)
        self.assertIsInstance(subscribers, ResultSet)
        self.assertEqual(set([subscriber1, subscriber2]), set(subscribers))

    def test_getStructuralSubscribers_recipients(self):
        # If provided, get_structural_subscribers() calls the appropriate
        # methods on a BugNotificationRecipients object.
        subscriber = self.factory.makePerson()
        login_person(subscriber)
        product, bug = self.make_product_with_bug()
        product.addBugSubscription(subscriber, subscriber)
        recipients = BugNotificationRecipients()
        subscribers = get_structural_subscribers(bug, recipients, None, None)
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
        # get_structural_subscribers() respects the given level.
        subscriber = self.factory.makePerson()
        login_person(subscriber)
        product, bug = self.make_product_with_bug()
        subscription = product.addBugSubscription(subscriber, subscriber)
        filter = subscription.bug_filters.one()
        filter.bug_notification_level = BugNotificationLevel.METADATA
        self.assertEqual(
            [subscriber], list(
                get_structural_subscribers(
                    bug, None, BugNotificationLevel.METADATA, None)))
        filter.bug_notification_level = BugNotificationLevel.METADATA
        self.assertEqual(
            [], list(
                get_structural_subscribers(
                    bug, None, BugNotificationLevel.COMMENTS, None)))
