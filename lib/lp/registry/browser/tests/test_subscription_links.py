# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for subscription links."""

__metaclass__ = type

import unittest
from zope.component import getUtility
from BeautifulSoup import BeautifulSoup

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.interaction import ANONYMOUS
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.testing.pages import (
    first_tag_by_class,
    )
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.app.browser.tales import MenuAPI

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

from lp.registry.interfaces.person import IPersonSet
from lp.services.features import (
    getFeatureFlag,
    get_relevant_feature_controller,
    )
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    celebrity_logged_in,
    person_logged_in,
    BrowserTestCase,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import ADMIN_EMAIL
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
    view = {None: '+index',
            'bugs': '+bugs-index',
            }
    def setUp(self):
        super(_TestStructSubs, self).setUp()
        self.regular_user = self.factory.makePerson()

    def create_view(self, user, rootsite=None):
        request = LaunchpadTestRequest(
            PATH_INFO='/', HTTP_COOKIE='',QUERY_STRING='')
        request.features = get_relevant_feature_controller()
        view = self.view.get(rootsite, '+index')
        return create_initialized_view(
            self.target, view, principal=user, rootsite=rootsite,
            request=request, current_request=False)

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
                view = self.create_view(user)
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestProductBugsStructSubs(TestProductViewStructSubs):
    """Test structural subscriptions on the product bugs view."""

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = ProductBugsMenu(self.target)
                view = self.create_view(user, rootsite='bugs')
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
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
                view = self.create_view(user)
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestProjectGroupBugsStructSubs(TestProjectGroupViewStructSubs):
    """Test structural subscriptions on the product bugs view."""

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = ProjectBugsMenu(self.target)
                view = self.create_view(user, rootsite='bugs')
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestProductSeriesViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the product view."""

    def setUp(self):
        super(TestProductSeriesViewStructSubs, self).setUp()
        self.target = self.factory.makeProductSeries()

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                self.assertEqual(flag, getFeatureFlag(self.feature_flag))
                menu = ProductSeriesOverviewMenu(self.target)
                view = self.create_view(user)
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestProductSeriesBugsStructSubs(TestProductSeriesViewStructSubs):
    """Test structural subscriptions on the product bugs view."""

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = ProductSeriesBugsMenu(self.target)
                view = self.create_view(user, rootsite='bugs')
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
                return menu.links, old_link, new_link


class TestDistroViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the distribution view.

    Distributions are special.  They are marked as
    IStructuralSubscriptionTargets but the functionality is not enabled.
    """

    def setUp(self):
        super(TestDistroViewStructSubs, self).setUp()
        self.target = self.factory.makeDistribution()
        self.target = getUtility(ILaunchpadCelebrities).ubuntu

    def _create_scenario(self, user, flag):
        if user != ANONYMOUS and user.is_team:
            user = user.teamowner
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = DistributionNavigationMenu(self.target)
                view = self.create_view(user)
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
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
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_anonymous(self):
        links, old_link, new_link = self._create_scenario(
            ANONYMOUS, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
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
        self.assertNotEqual(None, new_link, self.contents)
        self.assertEqual(None, old_link)

    def test_subscribe_link_feature_flag_off_bug_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        links, old_link, new_link = self._create_scenario(
            admin, None)
        self.assertTrue('subscribe' in links)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_bug_admin(self):
        from lp.testing.sampledata import ADMIN_EMAIL
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        links, old_link, new_link = self._create_scenario(
            admin, 'on')
        self.assertTrue('subscribe_to_bug_mail' in links)
        self.assertNotEqual(None, new_link, self.contents)
        self.assertEqual(None, old_link)


class TestDistroViewStructSubsTB(BrowserTestCase):
    """Test structural subscriptions on the distribution view.

    Distributions are special.  They are marked as
    IStructuralSubscriptionTargets but the functionality is not enabled.
    """

    layer = DatabaseFunctionalLayer
    feature_flag = 'malone.advanced-structural-subscriptions.enabled'
    rootsite = None
    view = '+index'

    def setUp(self):
        super(TestDistroViewStructSubsTB, self).setUp()
        self.target = self.factory.makeDistribution()
        with person_logged_in(self.target.owner):
            self.target.official_malone = True

        self.regular_user = self.factory.makePerson()

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                logged_in_user = getUtility(ILaunchBag).user
                browser = self.getViewBrowser(
                    self.target, view_name=self.view,
                    rootsite=self.rootsite,
                    user=logged_in_user)
                self.contents = browser.contents
                soup = BeautifulSoup(self.contents)
                href = canonical_url(
                    self.target, rootsite=self.rootsite,
                    view_name='+subscribe')
                old_link = soup.find('a', href=href)
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
                return old_link, new_link

    def test_subscribe_link_feature_flag_off_owner(self):
        old_link, new_link = self._create_scenario(
            self.target.owner, None)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)


    def test_subscribe_link_feature_flag_on_owner(self):
        old_link, new_link = self._create_scenario(
            self.target.owner, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

    def test_subscribe_link_feature_flag_off_user(self):
        old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_user_no_bug_super(self):
        old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_user_with_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            supervisor = self.factory.makePerson()
            self.target.setBugSupervisor(
                supervisor, admin)
        old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    # Can't do ANONYMOUS testing with BrowserTestCase as it creates a new,
    # valid user when it encounters ANONYMOUS.

    ## def test_subscribe_link_feature_flag_off_anonymous(self):
    ##     old_link, new_link = self._create_scenario(
    ##         ANONYMOUS, None)
    ##     self.assertEqual(None, old_link)
    ##     self.assertEqual(None, new_link)

    ## def test_subscribe_link_feature_flag_on_anonymous(self):
    ##     old_link, new_link = self._create_scenario(
    ##         ANONYMOUS, 'on')
    ##     self.assertEqual(None, new_link)
    ##     self.assertEqual(None, old_link)

    def test_subscribe_link_feature_flag_off_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertNotEqual(None, new_link, self.contents)
        self.assertEqual(None, old_link)

    def test_subscribe_link_feature_flag_off_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        old_link, new_link = self._create_scenario(
            admin, None)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_admin(self):
        from lp.testing.sampledata import ADMIN_EMAIL
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        old_link, new_link = self._create_scenario(
            admin, 'on')
        self.assertNotEqual(None, new_link, self.contents)
        self.assertEqual(None, old_link)


class TestDistroBugsStructSubsTB(TestDistroViewStructSubsTB):

    rootsite = 'bugs'
    view = '+bugs-index'

    def test_subscribe_link_feature_flag_off_owner(self):
        old_link, new_link = self._create_scenario(
            self.target.owner, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_owner(self):
        old_link, new_link = self._create_scenario(
            self.target.owner, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

    def test_subscribe_link_feature_flag_off_user(self):
        old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_user_no_bug_super(self):
        old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_user_with_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            supervisor = self.factory.makePerson()
            self.target.setBugSupervisor(
                supervisor, admin)
        old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    # Can't do ANONYMOUS testing with BrowserTestCase as it creates a new,
    # valid user when it encounters ANONYMOUS.

    ## def test_subscribe_link_feature_flag_off_anonymous(self):
    ##     old_link, new_link = self._create_scenario(
    ##         ANONYMOUS, None)
    ##     self.assertEqual(None, old_link)
    ##     self.assertEqual(None, new_link)

    ## def test_subscribe_link_feature_flag_on_anonymous(self):
    ##     old_link, new_link = self._create_scenario(
    ##         ANONYMOUS, 'on')
    ##     self.assertEqual(None, new_link)
    ##     self.assertEqual(None, old_link)

    def test_subscribe_link_feature_flag_off_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link, self.contents)

    def test_subscribe_link_feature_flag_off_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        old_link, new_link = self._create_scenario(
            admin, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_admin(self):
        from lp.testing.sampledata import ADMIN_EMAIL
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        old_link, new_link = self._create_scenario(
            admin, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link, self.contents)

class TestDistroBugsStructSubs(TestDistroViewStructSubs):
    """Test structural subscriptions on the distribution bugs view.

    Distributions are special.  They are marked as
    IStructuralSubscriptionTargets but the functionality is not enabled.
    """

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                menu = DistributionBugsMenu(self.target)
                view = self.create_view(user, rootsite='bugs')
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
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
                view = self.create_view(user)
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
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
                view = self.create_view(user, rootsite='bugs')
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
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
    suite.addTest(unittest.makeSuite(TestDistroViewStructSubsTB))
    suite.addTest(unittest.makeSuite(TestDistroBugsStructSubsTB))
    suite.addTest(unittest.makeSuite(TestDistroBugsStructSubs))
    suite.addTest(unittest.makeSuite(
        TestDistributionSourcePackageViewStructSubs))
    suite.addTest(unittest.makeSuite(
        TestDistributionSourcePackageBugsStructSubs))
    return suite
