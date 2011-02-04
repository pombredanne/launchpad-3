# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for structural subscription traversal."""

from urlparse import urlparse

from lazr.restful.testing.webservice import FakeRequest
import transaction
from zope.publisher.interfaces import NotFound

from canonical.launchpad.ftests import (
    LaunchpadFormHarness,
    login,
    logout,
    )
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import StepsToGo
from canonical.testing.layers import (
    AppServerLayer,
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.registry.browser.distribution import DistributionNavigation
from lp.registry.browser.distributionsourcepackage import (
    DistributionSourcePackageNavigation,
    )
from lp.registry.browser.distroseries import DistroSeriesNavigation
from lp.registry.browser.milestone import MilestoneNavigation
from lp.registry.browser.product import ProductNavigation
from lp.registry.browser.productseries import ProductSeriesNavigation
from lp.registry.browser.project import ProjectNavigation
from lp.registry.browser.structuralsubscription import (
    StructuralSubscriptionView,
    )
from lp.registry.enum import BugNotificationLevel
from lp.testing import (
    feature_flags,
    person_logged_in,
    set_feature_flag,
    TestCaseWithFactory,
    ws_object,
    )
from lp.testing.views import create_initialized_view


class FakeLaunchpadRequest(FakeRequest):

    @property
    def stepstogo(self):
        """See `IBasicLaunchpadRequest`."""
        return StepsToGo(self)


class StructuralSubscriptionTraversalTestBase(TestCaseWithFactory):
    """Verify that we can reach a target's structural subscriptions."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(StructuralSubscriptionTraversalTestBase, self).setUp()
        login('foo.bar@canonical.com')
        self.eric = self.factory.makePerson(name='eric')
        self.michael = self.factory.makePerson(name='michael')

        self.setUpTarget()
        self.target.addBugSubscription(self.eric, self.eric)

    def setUpTarget(self):
        self.target = self.factory.makeProduct(name='fooix')
        self.navigation = ProductNavigation

    def test_structural_subscription_traversal(self):
        # Verify that an existing structural subscription can be
        # reached from the target.
        request = FakeLaunchpadRequest([], ['eric'])
        self.assertEqual(
            self.target.getSubscription(self.eric),
            self.navigation(self.target, request).publishTraverse(
                request, '+subscription'))

    def test_missing_structural_subscription_traversal(self):
        # Verify that a NotFound is raised when attempting to reach
        # a structural subscription for an person without one.
        request = FakeLaunchpadRequest([], ['michael'])
        self.assertRaises(
            NotFound,
            self.navigation(self.target, request).publishTraverse,
            request, '+subscription')

    def test_missing_person_structural_subscription_traversal(self):
        # Verify that a NotFound is raised when attempting to reach
        # a structural subscription for a person that does not exist.
        request = FakeLaunchpadRequest([], ['doesnotexist'])
        self.assertRaises(
            NotFound,
            self.navigation(self.target, request).publishTraverse,
            request, '+subscription')

    def test_structural_subscription_canonical_url(self):
        # Verify that the canonical_url of a structural subscription
        # is correct.
        self.assertEqual(
            canonical_url(self.target.getSubscription(self.eric)),
            canonical_url(self.target) + '/+subscription/eric')

    def tearDown(self):
        logout()
        super(StructuralSubscriptionTraversalTestBase, self).tearDown()


class TestProductSeriesStructuralSubscriptionTraversal(
    StructuralSubscriptionTraversalTestBase):
    """Test IStructuralSubscription traversal from IProductSeries."""

    def setUpTarget(self):
        self.target = self.factory.makeProduct(name='fooix').newSeries(
            self.eric, '0.1', '0.1')
        self.navigation = ProductSeriesNavigation


class TestMilestoneStructuralSubscriptionTraversal(
    StructuralSubscriptionTraversalTestBase):
    """Test IStructuralSubscription traversal from IMilestone."""

    def setUpTarget(self):
        self.target = self.factory.makeProduct(name='fooix').newSeries(
            self.eric, '0.1', '0.1').newMilestone('0.1.0')
        self.navigation = MilestoneNavigation


class TestProjectStructuralSubscriptionTraversal(
    StructuralSubscriptionTraversalTestBase):
    """Test IStructuralSubscription traversal from IProjectGroup."""

    def setUpTarget(self):
        self.target = self.factory.makeProject(name='fooix-project')
        self.navigation = ProjectNavigation


class TestDistributionStructuralSubscriptionTraversal(
    StructuralSubscriptionTraversalTestBase):
    """Test IStructuralSubscription traversal from IDistribution."""

    def setUpTarget(self):
        self.target = self.factory.makeDistribution(name='debuntu')
        self.navigation = DistributionNavigation


class TestDistroSeriesStructuralSubscriptionTraversal(
    StructuralSubscriptionTraversalTestBase):
    """Test IStructuralSubscription traversal from IDistroSeries."""

    def setUpTarget(self):
        self.target = self.factory.makeDistribution(name='debuntu').newSeries(
            '5.0', '5.0', '5.0', '5.0', '5.0', '5.0', None, self.eric)
        self.navigation = DistroSeriesNavigation


class TestDistributionSourcePackageStructuralSubscriptionTraversal(
    StructuralSubscriptionTraversalTestBase):
    """Test IStructuralSubscription traversal from IDistributionSourcePackage.
    """

    def setUpTarget(self):
        debuntu = self.factory.makeDistribution(name='debuntu')
        fooix = self.factory.makeSourcePackageName('fooix')
        self.target = debuntu.getSourcePackage(fooix)
        self.navigation = DistributionSourcePackageNavigation


class TestStructuralSubscriptionAdvancedFeaturesBase(TestCaseWithFactory):
    """A base class for testing advanced structural subscription features."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscriptionAdvancedFeaturesBase, self).setUp()
        self.setUpTarget()
        with feature_flags():
            set_feature_flag(u'malone.advanced-subscriptions.enabled', u'on')

    def setUpTarget(self):
        self.target = self.factory.makeProduct()

    def test_subscribe_uses_bug_notification_level(self):
        # When advanced features are turned on for subscriptions a user
        # can specify a bug_notification_level on the +subscribe form.
        with feature_flags():
            # We don't display BugNotificationLevel.NOTHING as an option.
            displayed_levels = [
                level for level in BugNotificationLevel.items
                if level != BugNotificationLevel.NOTHING]
            for level in displayed_levels:
                person = self.factory.makePerson()
                with person_logged_in(person):
                    harness = LaunchpadFormHarness(
                        self.target, StructuralSubscriptionView)
                    form_data = {
                        'field.subscribe_me': 'on',
                        'field.bug_notification_level': level.title,
                        }
                    harness.submit('save', form_data)
                    self.assertFalse(harness.hasErrors())

                subscription = self.target.getSubscription(person)
                self.assertEqual(
                    level, subscription.bug_notification_level,
                    "Bug notification level of subscription should be %s, "
                    "is actually %s." % (
                        level.name, subscription.bug_notification_level.name))

    def test_subscribe_uses_bug_notification_level_for_teams(self):
        # The bug_notification_level field is also used when subscribing
        # a team.
        with feature_flags():
            displayed_levels = [
                level for level in BugNotificationLevel.items
                if level != BugNotificationLevel.NOTHING]
            for level in displayed_levels:
                person = self.factory.makePerson()
                team = self.factory.makeTeam(owner=person)
                with person_logged_in(person):
                    harness = LaunchpadFormHarness(
                        self.target, StructuralSubscriptionView)
                    form_data = {
                        'field.subscribe_me': '',
                        'field.subscriptions_team': team.name,
                        'field.bug_notification_level': level.title,
                        }
                    harness.submit('save', form_data)
                    self.assertFalse(harness.hasErrors())

                subscription = self.target.getSubscription(team)
                self.assertEqual(
                    level, subscription.bug_notification_level,
                    "Bug notification level of subscription should be %s, "
                    "is actually %s." % (
                        level.name, subscription.bug_notification_level.name))

    def test_nothing_is_not_a_valid_level(self):
        # BugNotificationLevel.NOTHING isn't considered valid when a
        # user is subscribing via the web UI.
        person = self.factory.makePerson()
        with feature_flags():
            with person_logged_in(person):
                harness = LaunchpadFormHarness(
                    self.target, StructuralSubscriptionView)
                form_data = {
                    'field.subscribe_me': 'on',
                    'field.bug_notification_level': (
                        BugNotificationLevel.NOTHING),
                    }
                harness.submit('save', form_data)
                self.assertTrue(harness.hasErrors())

    def test_extra_features_hidden_without_feature_flag(self):
        # If the malone.advanced-subscriptions.enabled flag is turned
        # off, the bug_notification_level field doesn't appear on the
        # form.
        person = self.factory.makePerson()
        with person_logged_in(person):
            harness = LaunchpadFormHarness(
                self.target, StructuralSubscriptionView)
            form_fields = harness.view.form_fields
            self.assertIs(
                None, form_fields.get('bug_notification_level'))


class TestProductSeriesAdvancedSubscriptionFeatures(
    TestStructuralSubscriptionAdvancedFeaturesBase):
    """Test advanced subscription features for ProductSeries."""

    def setUpTarget(self):
        self.target = self.factory.makeProductSeries()


class TestDistributionAdvancedSubscriptionFeatures(
    TestStructuralSubscriptionAdvancedFeaturesBase):
    """Test advanced subscription features for distributions."""

    def setUpTarget(self):
        self.target = self.factory.makeDistribution()


class TestDistroSeriesAdvancedSubscriptionFeatures(
    TestStructuralSubscriptionAdvancedFeaturesBase):
    """Test advanced subscription features for DistroSeries."""

    def setUpTarget(self):
        self.target = self.factory.makeDistroSeries()


class TestMilestoneAdvancedSubscriptionFeatures(
    TestStructuralSubscriptionAdvancedFeaturesBase):
    """Test advanced subscription features for Milestones."""

    def setUpTarget(self):
        self.target = self.factory.makeMilestone()


class TestStructuralSubscriptionView(TestCaseWithFactory):
    """General tests for the StructuralSubscriptionView."""

    layer = DatabaseFunctionalLayer

    def test_next_url_set_to_context(self):
        # When the StructuralSubscriptionView form is submitted, the
        # view's next_url is set to the canonical_url of the current
        # target.
        target = self.factory.makeProduct()
        person = self.factory.makePerson()
        with person_logged_in(person):
            view = create_initialized_view(target, name='+subscribe')
            self.assertEqual(
                canonical_url(target), view.next_url,
                "Next URL does not match target's canonical_url.")


class TestStructuralSubscribersPortletViewBase(TestCaseWithFactory):
    """General tests for the StructuralSubscribersPortletView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestStructuralSubscribersPortletViewBase, self).setUp()
        self.setUpTarget()
        self.view = create_initialized_view(
            self.target, name='+portlet-structural-subscribers')

    def setUpTarget(self):
        project = self.factory.makeProject()
        self.target = self.factory.makeProduct(project=project)

    def test_target_label(self):
        # The target_label attribute of StructuralSubscribersPortletView
        # returns the correct label for the current
        # StructuralSubscriptionTarget.
        self.assertEqual(
            "To all %s bugs" % self.target.title, self.view.target_label)

    def test_parent_target_label(self):
        # The parent_target_label attribute of
        # StructuralSubscribersPortletView returns the correct label for
        # the current parent StructuralSubscriptionTarget.
        self.assertEqual(
            "To all %s bugs" % self.target.parent_subscription_target.title,
            self.view.parent_target_label)


class TestSourcePackageStructuralSubscribersPortletView(
    TestStructuralSubscribersPortletViewBase):

    def setUpTarget(self):
        distribution = self.factory.makeDistribution()
        sourcepackage = self.factory.makeSourcePackageName()
        self.target = distribution.getSourcePackage(sourcepackage.name)

    def test_target_label(self):
        # For DistributionSourcePackages the target_label attribute uses
        # the target's displayname rather than its title.
        self.assertEqual(
            "To all bugs in %s" % self.target.displayname,
            self.view.target_label)


class TestStructuralSubscriptionAPI(TestCaseWithFactory):

    layer = AppServerLayer

    def setUp(self):
        super(TestStructuralSubscriptionAPI, self).setUp()
        self.owner = self.factory.makePerson(name=u"foo")
        self.structure = self.factory.makeProduct(
            owner=self.owner, name=u"bar")
        with person_logged_in(self.owner):
            self.subscription = self.structure.addBugSubscription(
                self.owner, self.owner)
        transaction.commit()
        self.service = self.factory.makeLaunchpadService(self.owner)
        self.ws_subscription = ws_object(self.service, self.subscription)

    def test_newBugFilter(self):
        # New bug subscription filters can be created with newBugFilter().
        ws_subscription_filter = self.ws_subscription.newBugFilter()
        self.assertEqual(
            "bug_subscription_filter",
            urlparse(ws_subscription_filter.resource_type_link).fragment)
        self.assertEqual(
            ws_subscription_filter.structural_subscription.self_link,
            self.ws_subscription.self_link)

    def test_bug_filters(self):
        # The bug_filters property is a collection of IBugSubscriptionFilter
        # instances previously created by newBugFilter().
        bug_filter_links = lambda: set(
            bug_filter.self_link for bug_filter in (
                self.ws_subscription.bug_filters))
        self.assertEqual(set(), bug_filter_links())
        # A new filter appears in the bug_filters collection.
        ws_subscription_filter1 = self.ws_subscription.newBugFilter()
        self.assertEqual(
            set([ws_subscription_filter1.self_link]),
            bug_filter_links())
        # A second new filter also appears in the bug_filters collection.
        ws_subscription_filter2 = self.ws_subscription.newBugFilter()
        self.assertEqual(
            set([ws_subscription_filter1.self_link,
                 ws_subscription_filter2.self_link]),
            bug_filter_links())
