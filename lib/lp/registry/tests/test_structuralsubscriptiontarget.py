# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running tests against IStructuralsubscriptionTarget
implementations.
"""
__metaclass__ = type

import unittest

from storm.expr import compile as compile_storm
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
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.bugs.interfaces.bug import CreateBugParams
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    )
from lp.bugs.model.bugsubscriptionfilter import BugSubscriptionFilter
from lp.bugs.tests.test_bugtarget import bugtarget_filebug
from lp.registry.enum import BugNotificationLevel
from lp.registry.errors import (
    DeleteSubscriptionError,
    UserCannotSubscribePerson,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.registry.interfaces.structuralsubscription import (
    IStructuralSubscriptionTarget,
    IStructuralSubscriptionTargetHelper,
    )
from lp.registry.model.structuralsubscription import StructuralSubscription
from lp.testing import (
    ANONYMOUS,
    login,
    login_celebrity,
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.matchers import Provides


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


class FilteredStructuralSubscriptionTestBase(StructuralSubscriptionTestBase):
    """Tests for filtered structural subscriptions."""

    def makeBugTask(self):
        return self.factory.makeBugTask(target=self.target)

    def test_getSubscriptionsForBugTask(self):
        # If no one has a filtered subscription for the given bug, the result
        # of getSubscriptionsForBugTask() is the same as for
        # getSubscriptions().
        bugtask = self.makeBugTask()
        subscriptions = self.target.getSubscriptions(
            min_bug_notification_level=BugNotificationLevel.NOTHING)
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual(list(subscriptions), list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_filter_on_status(self):
        # If a status filter exists for a subscription, the result of
        # getSubscriptionsForBugTask() may be a subset of getSubscriptions().
        bugtask = self.makeBugTask()

        # Create a new subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.COMMENTS

        # Without any filters the subscription is found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

        # Filter the subscription to bugs in the CONFIRMED state.
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structural_subscription = subscription
        subscription_filter.statuses = [BugTaskStatus.CONFIRMED]

        # With the filter the subscription is not found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # If the filter is adjusted, the subscription is found again.
        subscription_filter.statuses = [bugtask.status]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_filter_on_importance(self):
        # If an importance filter exists for a subscription, the result of
        # getSubscriptionsForBugTask() may be a subset of getSubscriptions().
        bugtask = self.makeBugTask()

        # Create a new subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.COMMENTS

        # Without any filters the subscription is found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

        # Filter the subscription to bugs in the CRITICAL state.
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structural_subscription = subscription
        subscription_filter.importances = [BugTaskImportance.CRITICAL]

        # With the filter the subscription is not found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # If the filter is adjusted, the subscription is found again.
        subscription_filter.importances = [bugtask.importance]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_filter_on_level(self):
        # All structural subscriptions have a level for bug notifications
        # which getSubscriptionsForBugTask() observes.
        bugtask = self.makeBugTask()

        # Create a new METADATA level subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.METADATA

        # The subscription is found when looking for NOTHING or above.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))
        # The subscription is found when looking for METADATA or above.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.METADATA)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))
        # The subscription is not found when looking for COMMENTS or above.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.COMMENTS)
        self.assertEqual([], list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_filter_include_any_tags(self):
        # If a subscription filter has include_any_tags, a bug with one or
        # more tags is matched.
        bugtask = self.makeBugTask()

        # Create a new subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.COMMENTS
        subscription_filter = subscription.newBugFilter()
        subscription_filter.include_any_tags = True

        # Without any tags the subscription is not found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # With any tag the subscription is found.
        bugtask.bug.tags = ["foo"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_filter_exclude_any_tags(self):
        # If a subscription filter has exclude_any_tags, only bugs with no
        # tags are matched.
        bugtask = self.makeBugTask()

        # Create a new subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.COMMENTS
        subscription_filter = subscription.newBugFilter()
        subscription_filter.exclude_any_tags = True

        # Without any tags the subscription is found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

        # With any tag the subscription is not found.
        bugtask.bug.tags = ["foo"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_filter_for_any_tag(self):
        # If a subscription filter specifies that any of one or more specific
        # tags must be present, bugs with any of those tags are matched.
        bugtask = self.makeBugTask()

        # Create a new subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.COMMENTS
        subscription_filter = subscription.newBugFilter()

        # Looking for either the "foo" or the "bar" tag.
        subscription_filter.tags = [u"foo", u"bar"]
        subscription_filter.find_all_tags = False

        # Without either tag the subscription is not found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # With either tag the subscription is found.
        bugtask.bug.tags = ["bar", "baz"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_filter_for_all_tags(self):
        # If a subscription filter specifies that all of one or more specific
        # tags must be present, bugs with all of those tags are matched.
        bugtask = self.makeBugTask()

        # Create a new subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.COMMENTS
        subscription_filter = subscription.newBugFilter()

        # Looking for both the "foo" and the "bar" tag.
        subscription_filter.tags = [u"foo", u"bar"]
        subscription_filter.find_all_tags = True

        # Without either tag the subscription is not found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # Without only one of the required tags the subscription is not found.
        bugtask.bug.tags = ["foo"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # With both required tags the subscription is found.
        bugtask.bug.tags = ["foo", "bar"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_filter_for_not_any_tag(self):
        # If a subscription filter specifies that any of one or more specific
        # tags must not be present, bugs without any of those tags are
        # matched.
        bugtask = self.makeBugTask()

        # Create a new subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.COMMENTS
        subscription_filter = subscription.newBugFilter()

        # Looking to exclude the "foo" or "bar" tags.
        subscription_filter.tags = [u"-foo", u"-bar"]
        subscription_filter.find_all_tags = False

        # Without either tag the subscription is found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

        # With either tag the subscription is no longer found.
        bugtask.bug.tags = ["foo"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_filter_for_not_all_tags(self):
        # If a subscription filter specifies that all of one or more specific
        # tags must not be present, bugs without all of those tags are
        # matched.
        bugtask = self.makeBugTask()

        # Create a new subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.COMMENTS
        subscription_filter = subscription.newBugFilter()

        # Looking to exclude the "foo" and "bar" tags.
        subscription_filter.tags = [u"-foo", u"-bar"]
        subscription_filter.find_all_tags = True

        # Without either tag the subscription is found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

        # With only one of the excluded tags the subscription is found.
        bugtask.bug.tags = ["foo"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

        # With both tags the subscription is no longer found.
        bugtask.bug.tags = ["foo", "bar"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

    def test_getSubscriptionsForBugTask_with_multiple_filters(self):
        # If multiple filters exist for a subscription, all filters must
        # match.
        bugtask = self.makeBugTask()

        # Create a new subscription on self.target.
        login_person(self.ordinary_subscriber)
        subscription = self.target.addSubscription(
            self.ordinary_subscriber, self.ordinary_subscriber)
        subscription.bug_notification_level = BugNotificationLevel.COMMENTS

        # Add the "foo" tag to the bug.
        bugtask.bug.tags = ["foo"]

        # Filter the subscription to bugs in the CRITICAL state.
        subscription_filter = BugSubscriptionFilter()
        subscription_filter.structural_subscription = subscription
        subscription_filter.statuses = [BugTaskStatus.CONFIRMED]
        subscription_filter.importances = [BugTaskImportance.CRITICAL]

        # With the filter the subscription is not found.
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # If the filter is adjusted to match status but not importance, the
        # subscription is still not found.
        subscription_filter.statuses = [bugtask.status]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # If the filter is adjusted to also match importance, the subscription
        # is found again.
        subscription_filter.importances = [bugtask.importance]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

        # If the filter is given some tag criteria, the subscription is not
        # found.
        subscription_filter.tags = [u"-foo", u"bar", u"baz"]
        subscription_filter.find_all_tags = False
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # After removing the "foo" tag and adding the "bar" tag, the
        # subscription is found.
        bugtask.bug.tags = ["bar"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))

        # Requiring that all tag criteria are fulfilled causes the
        # subscription to no longer be found.
        subscription_filter.find_all_tags = True
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([], list(subscriptions_for_bugtask))

        # After adding the "baz" tag, the subscription is found again.
        bugtask.bug.tags = ["bar", "baz"]
        subscriptions_for_bugtask = self.target.getSubscriptionsForBugTask(
            bugtask, BugNotificationLevel.NOTHING)
        self.assertEqual([subscription], list(subscriptions_for_bugtask))


class TestStructuralSubscriptionForDistro(
    FilteredStructuralSubscriptionTestBase, TestCaseWithFactory):

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
    UnrestrictedStructuralSubscription,
    FilteredStructuralSubscriptionTestBase,
    TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForProduct, self).setUp()
        self.target = self.factory.makeProduct()


class TestStructuralSubscriptionForDistroSourcePackage(
    UnrestrictedStructuralSubscription,
    FilteredStructuralSubscriptionTestBase,
    TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForDistroSourcePackage, self).setUp()
        self.target = self.factory.makeDistributionSourcePackage()
        self.target = ProxyFactory(self.target)


class TestStructuralSubscriptionForMilestone(
    UnrestrictedStructuralSubscription,
    FilteredStructuralSubscriptionTestBase,
    TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForMilestone, self).setUp()
        self.target = self.factory.makeMilestone()
        self.target = ProxyFactory(self.target)

    def makeBugTask(self):
        # XXX Should test with target *and* series_target.
        return self.factory.makeBugTask(target=self.target.series_target)


class TestStructuralSubscriptionForDistroSeries(
    UnrestrictedStructuralSubscription,
    FilteredStructuralSubscriptionTestBase,
    TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForDistroSeries, self).setUp()
        self.target = self.factory.makeDistroSeries()
        self.target = ProxyFactory(self.target)


class TestStructuralSubscriptionForProjectGroup(
    UnrestrictedStructuralSubscription,
    FilteredStructuralSubscriptionTestBase,
    TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForProjectGroup, self).setUp()
        self.target = self.factory.makeProject()
        self.target = ProxyFactory(self.target)

    def makeBugTask(self):
        return self.factory.makeBugTask(
            target=self.factory.makeProduct(project=self.target))


class TestStructuralSubscriptionForProductSeries(
    UnrestrictedStructuralSubscription,
    FilteredStructuralSubscriptionTestBase,
    TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionForProductSeries, self).setUp()
        self.target = self.factory.makeProductSeries()
        self.target = ProxyFactory(self.target)


class TestStructuralSubscriptionTargetHelper(TestCaseWithFactory):
    """Tests for implementations of `IStructuralSubscriptionTargetHelper`."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestStructuralSubscriptionTargetHelper, self).setUp()
        self.person = self.factory.makePerson()
        login_person(self.person)

    def test_distribution_series(self):
        target = self.factory.makeDistroSeries()
        helper = IStructuralSubscriptionTargetHelper(target)
        self.assertThat(helper, Provides(IStructuralSubscriptionTargetHelper))
        self.assertEqual("distribution series", helper.target_type_display)
        self.assertEqual(target, helper.target)
        self.assertEqual(target.distribution, helper.target_parent)
        self.assertEqual({"distroseries": target}, helper.target_arguments)
        self.assertEqual(target.distribution, helper.pillar)
        self.assertEqual(
            u"StructuralSubscription.distroseries = ?",
            compile_storm(helper.join))

    def test_project_group(self):
        target = self.factory.makeProject(owner=self.person)
        helper = IStructuralSubscriptionTargetHelper(target)
        self.assertThat(helper, Provides(IStructuralSubscriptionTargetHelper))
        self.assertEqual("project group", helper.target_type_display)
        self.assertEqual(target, helper.target)
        self.assertEqual(None, helper.target_parent)
        self.assertEqual(target, helper.pillar)
        self.assertEqual({"project": target}, helper.target_arguments)
        self.assertEqual(
            u"StructuralSubscription.project = ?",
            compile_storm(helper.join))

    def test_distribution_source_package(self):
        target = self.factory.makeDistributionSourcePackage()
        helper = IStructuralSubscriptionTargetHelper(target)
        self.assertThat(helper, Provides(IStructuralSubscriptionTargetHelper))
        self.assertEqual("package", helper.target_type_display)
        self.assertEqual(target, helper.target)
        self.assertEqual(target.distribution, helper.target_parent)
        self.assertThat(
            helper.target_parent, Provides(IStructuralSubscriptionTarget))
        self.assertEqual(target.distribution, helper.pillar)
        self.assertEqual(
            {"distribution": target.distribution,
             "sourcepackagename": target.sourcepackagename},
            helper.target_arguments)
        self.assertEqual(
            u"StructuralSubscription.distribution = ? AND "
            u"StructuralSubscription.sourcepackagename = ?",
            compile_storm(helper.join))

    def test_milestone(self):
        target = self.factory.makeMilestone()
        helper = IStructuralSubscriptionTargetHelper(target)
        self.assertThat(helper, Provides(IStructuralSubscriptionTargetHelper))
        self.assertEqual("milestone", helper.target_type_display)
        self.assertEqual(target, helper.target)
        self.assertEqual(target.target, helper.target_parent)
        self.assertThat(
            helper.target_parent, Provides(IStructuralSubscriptionTarget))
        self.assertEqual(target.target, helper.pillar)
        self.assertEqual({"milestone": target}, helper.target_arguments)
        self.assertEqual(
            u"StructuralSubscription.milestone = ?",
            compile_storm(helper.join))

    def test_product(self):
        target = self.factory.makeProduct(owner=self.person)
        helper = IStructuralSubscriptionTargetHelper(target)
        self.assertThat(helper, Provides(IStructuralSubscriptionTargetHelper))
        self.assertEqual("project", helper.target_type_display)
        self.assertEqual(target, helper.target)
        self.assertEqual(None, helper.target_parent)
        self.assertEqual(target, helper.pillar)
        self.assertEqual({"product": target}, helper.target_arguments)
        self.assertEqual(
            u"StructuralSubscription.product = ?",
            compile_storm(helper.join))

    def test_product_in_group(self):
        project = self.factory.makeProject(owner=self.person)
        target = self.factory.makeProduct(project=project)
        helper = IStructuralSubscriptionTargetHelper(target)
        self.assertThat(helper, Provides(IStructuralSubscriptionTargetHelper))
        self.assertEqual("project", helper.target_type_display)
        self.assertEqual(target, helper.target)
        self.assertEqual(project, helper.target_parent)
        self.assertEqual(target, helper.pillar)
        self.assertEqual({"product": target}, helper.target_arguments)
        self.assertEqual(
            u"StructuralSubscription.product = ?",
            compile_storm(helper.join))

    def test_product_series(self):
        target = self.factory.makeProductSeries(owner=self.person)
        helper = IStructuralSubscriptionTargetHelper(target)
        self.assertThat(helper, Provides(IStructuralSubscriptionTargetHelper))
        self.assertEqual("project series", helper.target_type_display)
        self.assertEqual(target, helper.target)
        self.assertEqual(target.product, helper.target_parent)
        self.assertThat(
            helper.target_parent, Provides(IStructuralSubscriptionTarget))
        self.assertEqual(target.product, helper.pillar)
        self.assertEqual({"productseries": target}, helper.target_arguments)
        self.assertEqual(
            u"StructuralSubscription.productseries = ?",
            compile_storm(helper.join))

    def test_distribution(self):
        target = self.factory.makeDistribution(owner=self.person)
        helper = IStructuralSubscriptionTargetHelper(target)
        self.assertThat(helper, Provides(IStructuralSubscriptionTargetHelper))
        self.assertEqual(target, helper.target)
        self.assertEqual("distribution", helper.target_type_display)
        self.assertEqual(None, helper.target_parent)
        self.assertEqual(target, helper.pillar)
        self.assertEqual(
            {"distribution": target,
             "sourcepackagename": None},
            helper.target_arguments)
        self.assertEqual(
            u"StructuralSubscription.distribution = ? AND "
            u"StructuralSubscription.sourcepackagename IS NULL",
            compile_storm(helper.join))


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
