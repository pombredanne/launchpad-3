# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for subscription links."""

__metaclass__ = type

import unittest
from zope.component import getUtility

from canonical.launchpad.webapp.interaction import ANONYMOUS
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.testing.pages import (
    first_tag_by_class,
    )
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.registry.browser.product import (
    ProductActionNavigationMenu,
    ProductBugsMenu,
    )
from lp.registry.browser.productseries import (
    ProductSeriesOverviewMenu,
    ProductSeriesBugsMenu,
    )
from lp.registry.browser.project import (
    ProjectActionMenu,
    ProjectBugsMenu,
    )
from lp.registry.browser.distribution import (
    DistributionBugsMenu,
    DistributionNavigationMenu,
    )
from lp.registry.browser.distributionsourcepackage import (
    DistributionSourcePackageActionMenu,
    DistributionSourcePackageBugsMenu,
    )

from lp.services.features.testing import FeatureFixture
from lp.testing import (
    celebrity_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import (
    create_initialized_view,
    )


class _TestStructSubs(TestCaseWithFactory):
    """Test structural subscriptions base class.

    The link to structural subscriptions is controlled by the feature flag
    'malone.advanced-structural-subscriptions.enabled'.  If it is false, the
    old link leading to +subscribe is shown.  If it is true then the new
    JavaScript control is used.
    """

    layer = DatabaseFunctionalLayer
    feature_flag = 'malone.advanced-structural-subscriptions.enabled'

    def setUp(self):
        super(_TestStructSubs, self).setUp()
        self.regular_user = self.factory.makePerson()

    def test_subscribe_link_feature_flag_off_owner(self):
        links, old_link, new_link = self._create_scenario(
            self.target.owner, None)
        self.assertTrue('subscribe' in links)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)


    def test_subscribe_link_feature_flag_on_owner(self):
        # Test the new subscription link.
        links, old_link, new_link = self._create_scenario(
            self.target.owner, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
        self.assertNotEqual(None, new_link)
        self.assertEqual(None, old_link)

    def test_subscribe_link_feature_flag_off_user(self):
        links, old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertTrue('subscribe' in links)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)


    def test_subscribe_link_feature_flag_on_user(self):
        links, old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
        self.assertNotEqual(None, new_link)
        self.assertEqual(None, old_link)

    def test_subscribe_link_feature_flag_off_anonymous(self):
        links, old_link, new_link = self._create_scenario(
            ANONYMOUS, None)
        self.assertTrue('subscribe' in links)
        # The old subscribe link is actually shown to anonymous users but the
        # behavior has changed with the new link.
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_anonymous(self):
        links, old_link, new_link = self._create_scenario(
            ANONYMOUS, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
        # The subscribe link is not shown to anonymous.
        self.assertEqual(None, new_link)
        self.assertEqual(None, old_link)


class TestProductViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the product view."""

    def setUp(self):
        super(TestProductViewStructSubs, self).setUp()
        self.target = self.factory.makeProduct()

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = ProductActionNavigationMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestProductBugsStructSubs(TestProductViewStructSubs):
    """Test structural subscriptions on the product bugs view."""

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = ProductBugsMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', rootsite='bugs', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestProjectGroupViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the product view."""

    def setUp(self):
        super(TestProjectGroupViewStructSubs, self).setUp()
        self.target = self.factory.makeProject()

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = ProjectActionMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestProjectGroupBugsStructSubs(TestProjectGroupViewStructSubs):
    """Test structural subscriptions on the product bugs view."""

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = ProjectBugsMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', rootsite='bugs', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestProductSeriesViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the product view."""

    def setUp(self):
        super(TestProductSeriesViewStructSubs, self).setUp()
        self.target = self.factory.makeProductSeries()

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = ProductSeriesOverviewMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestProductSeriesBugsStructSubs(TestProductSeriesViewStructSubs):
    """Test structural subscriptions on the product bugs view."""

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = ProductSeriesBugsMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', rootsite='bugs', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestDistroViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the distribution view.

    Distributions are special.  They are marked as
    IStructuralSubscriptionTargets but the functionality is not enabled.
    """

    def setUp(self):
        super(TestDistroViewStructSubs, self).setUp()
        self.target = self.factory.makeDistribution()

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = DistributionNavigationMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link

    def test_subscribe_link_feature_flag_off_owner(self):
        links, old_link, new_link = self._create_scenario(
            self.target.owner, None)
        self.assertTrue('subscribe' in links)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)


    def test_subscribe_link_feature_flag_on_owner(self):
        links, old_link, new_link = self._create_scenario(
            self.target.owner, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_off_user(self):
        links, old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertTrue('subscribe' in links)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_user(self):
        links, old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_off_anonymous(self):
        links, old_link, new_link = self._create_scenario(
            ANONYMOUS, None)
        self.assertTrue('subscribe' in links)
        # The old subscribe link is actually shown to anonymous users but the
        # behavior has changed with the new link.
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_anonymous(self):
        links, old_link, new_link = self._create_scenario(
            ANONYMOUS, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
        # The subscribe link is not shown to anonymous.
        self.assertEqual(None, new_link)
        self.assertEqual(None, old_link)

    def test_subscribe_link_feature_flag_off_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        links, old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertTrue('subscribe' in links)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        links, old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
        self.assertNotEqual(None, new_link)
        self.assertEqual(None, old_link)


class TestDistroBugsStructSubs(TestDistroViewStructSubs):
    """Test structural subscriptions on the distribution bugs view.

    Distributions are special.  They are marked as
    IStructuralSubscriptionTargets but the functionality is not enabled.
    """

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = DistributionBugsMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', rootsite='bugs', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link

    def test_subscribe_link_feature_flag_off_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        links, old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertTrue('subscribe' in links)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        links, old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
        self.assertNotEqual(None, new_link)
        self.assertEqual(None, old_link)


class TestDistributionSourcePackageViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the product view."""

    def setUp(self):
        super(TestDistributionSourcePackageViewStructSubs, self).setUp()
        self.target = self.factory.makeDistributionSourcePackage()
        self.regular_user = self.factory.makePerson()

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = DistributionSourcePackageActionMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link

    # DistributionSourcePackages do not have owners.
    test_subscribe_link_feature_flag_off_owner = None
    test_subscribe_link_feature_flag_on_owner = None


class TestDistributionSourcePackageBugsStructSubs(
    TestDistributionSourcePackageViewStructSubs):
    """Test structural subscriptions on the product bugs view."""

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = DistributionSourcePackageBugsMenu(self.target)
                view = create_initialized_view(
                    self.target, '+index', rootsite='bugs', principal=user)
                html = view.render()
                old_link = first_tag_by_class(html, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    html, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


def test_suite():
    """Return the `IStructuralSubscriptionTarget` TestSuite."""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestProductViewStructSubs))
    suite.addTest(unittest.makeSuite(TestProductBugsStructSubs))
    suite.addTest(unittest.makeSuite(TestProductSeriesViewStructSubs))
    suite.addTest(unittest.makeSuite(TestProductSeriesBugsStructSubs))
    suite.addTest(unittest.makeSuite(TestProjectGroupViewStructSubs))
    suite.addTest(unittest.makeSuite(TestProjectGroupBugsStructSubs))
    suite.addTest(unittest.makeSuite(TestDistroViewStructSubs))
    suite.addTest(unittest.makeSuite(TestDistroBugsStructSubs))
    suite.addTest(unittest.makeSuite(
        TestDistributionSourcePackageViewStructSubs))
    suite.addTest(unittest.makeSuite(
        TestDistributionSourcePackageBugsStructSubs))
    return suite
