# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for subscription links."""

__metaclass__ = type

import unittest
from zope.component import getUtility
from BeautifulSoup import BeautifulSoup

from canonical.launchpad.webapp.interaction import ANONYMOUS
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.testing.pages import (
    first_tag_by_class,
    )
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.registry.interfaces.person import IPersonSet
from lp.services.features import (
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

    def setUp(self):
        super(_TestStructSubs, self).setUp()
        self.regular_user = self.factory.makePerson()

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                view = self.create_view(user)
                self.contents = view.render()
                old_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe')
                new_link = first_tag_by_class(
                    self.contents, 'menu-link-subscribe_to_bug_mail')
                return old_link, new_link

    def create_view(self, user):
        request = LaunchpadTestRequest(
            PATH_INFO='/', HTTP_COOKIE='', QUERY_STRING='')
        request.features = get_relevant_feature_controller()
        return create_initialized_view(
            self.target, self.view, principal=user,
            rootsite=self.rootsite,
            request=request, current_request=False)

    def test_subscribe_link_feature_flag_off_owner(self):
        old_link, new_link = self._create_scenario(
            self.target.owner, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_owner(self):
        # Test the new subscription link.
        old_link, new_link = self._create_scenario(
            self.target.owner, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

    def test_subscribe_link_feature_flag_off_user(self):
        old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_user(self):
        old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

    def test_subscribe_link_feature_flag_off_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, None)
        # The old subscribe link is actually shown to anonymous users but the
        # behavior has changed with the new link.
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, 'on')
        # The subscribe link is not shown to anonymous.
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)


class TestProductViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the product view."""

    rootsite = None
    view = '+index'

    def setUp(self):
        super(TestProductViewStructSubs, self).setUp()
        self.target = self.factory.makeProduct(official_malone=True)


class TestProductBugsStructSubs(TestProductViewStructSubs):
    """Test structural subscriptions on the product bugs view."""

    rootsite = 'bugs'
    view = '+bugs-index'


class TestProjectGroupViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the project group view."""

    rootsite = None
    view = '+index'

    def setUp(self):
        super(TestProjectGroupViewStructSubs, self).setUp()
        self.target = self.factory.makeProject()
        self.factory.makeProduct(
            project=self.target, official_malone=True)


class TestProjectGroupBugsStructSubs(TestProjectGroupViewStructSubs):
    """Test structural subscriptions on the project group bugs view."""

    rootsite = 'bugs'
    view = '+bugs'


class TestProductSeriesViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the product series view."""

    rootsite = None
    view = '+index'

    def setUp(self):
        super(TestProductSeriesViewStructSubs, self).setUp()
        self.target = self.factory.makeProductSeries()


class TestProductSeriesBugsStructSubs(TestProductSeriesViewStructSubs):
    """Test structural subscriptions on the product series bugs view."""

    rootsite = 'bugs'
    view = '+bugs-index'

    def setUp(self):
        super(TestProductSeriesBugsStructSubs, self).setUp()
        with person_logged_in(self.target.product.owner):
            self.target.product.official_malone = True


class TestDistributionSourcePackageViewStructSubs(_TestStructSubs):
    """Test structural subscriptions on the distro src pkg view."""

    rootsite = None
    view = '+index'

    def setUp(self):
        super(TestDistributionSourcePackageViewStructSubs, self).setUp()
        distro = self.factory.makeDistribution()
        with person_logged_in(distro.owner):
            distro.official_malone = True
        self.target = self.factory.makeDistributionSourcePackage(
            distribution=distro)
        self.regular_user = self.factory.makePerson()

    # DistributionSourcePackages do not have owners.
    test_subscribe_link_feature_flag_off_owner = None
    test_subscribe_link_feature_flag_on_owner = None


class TestDistributionSourcePackageBugsStructSubs(
    TestDistributionSourcePackageViewStructSubs):
    """Test structural subscriptions on the distro src pkg bugs view."""

    rootsite = 'bugs'
    view = '+bugs'


class TestDistroViewStructSubs(BrowserTestCase):
    """Test structural subscriptions on the distribution view.

    Distributions are special.  They are IStructuralSubscriptionTargets but
    have complicated rules to ensure Ubuntu users don't subscribe and become
    overwhelmed with email.  If a distro does not have a bug supervisor set,
    then anyone can create a structural subscription for themselves.  If the
    bug supervisor is set, then only people in the bug supervisor team can
    subscribe themselves.  Admins can subscribe anyone.
    """

    layer = DatabaseFunctionalLayer
    feature_flag = 'malone.advanced-structural-subscriptions.enabled'
    rootsite = None
    view = '+index'

    def setUp(self):
        super(TestDistroViewStructSubs, self).setUp()
        self.target = self.factory.makeDistribution()
        with person_logged_in(self.target.owner):
            self.target.official_malone = True
        self.regular_user = self.factory.makePerson()

    def _create_scenario(self, user, flag):
        with person_logged_in(user):
            with FeatureFixture({self.feature_flag: flag}):
                logged_in_user = getUtility(ILaunchBag).user
                no_login = logged_in_user is None
                browser = self.getViewBrowser(
                    self.target, view_name=self.view,
                    rootsite=self.rootsite,
                    no_login=no_login,
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

    def test_subscribe_link_feature_flag_off_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, None)
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, 'on')
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

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
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

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
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)


class TestDistroBugsStructSubs(TestDistroViewStructSubs):
    """Test structural subscriptions on the distro bugs view."""

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

    def test_subscribe_link_feature_flag_off_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, 'on')
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

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
        self.assertNotEqual(None, new_link)

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
        self.assertNotEqual(None, new_link)


class TestDistroMilestoneViewStructSubs(TestDistroViewStructSubs):
    """Test structural subscriptions on the distro milestones."""

    def setUp(self):
        super(TestDistroMilestoneViewStructSubs, self).setUp()
        self.distro = self.target
        self.target = self.factory.makeMilestone(distribution=self.distro)

    def test_subscribe_link_feature_flag_off_owner(self):
        old_link, new_link = self._create_scenario(
            self.distro.owner, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_owner(self):
        old_link, new_link = self._create_scenario(
            self.distro.owner, 'on')
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
            self.distro.setBugSupervisor(
                supervisor, admin)
        old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

    def test_subscribe_link_feature_flag_off_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, 'on')
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_off_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.distro.setBugSupervisor(
                self.regular_user, admin)
        old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.distro.setBugSupervisor(
                self.regular_user, admin)
        old_link, new_link = self._create_scenario(
            self.regular_user, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

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
        self.assertNotEqual(None, new_link)


class TestProductMilestoneViewStructSubs(TestDistroViewStructSubs):
    """Test structural subscriptions on the product milestones."""

    def setUp(self):
        super(TestProductMilestoneViewStructSubs, self).setUp()
        self.product = self.factory.makeProduct()
        with person_logged_in(self.product.owner):
            self.product.official_malone = True
        self.regular_user = self.factory.makePerson()
        self.target = self.factory.makeMilestone(product=self.product)

    def test_subscribe_link_feature_flag_off_owner(self):
        old_link, new_link = self._create_scenario(
            self.product.owner, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_owner(self):
        old_link, new_link = self._create_scenario(
            self.product.owner, 'on')
        self.assertEqual(None, old_link)
        self.assertNotEqual(None, new_link)

    def test_subscribe_link_feature_flag_off_user(self):
        old_link, new_link = self._create_scenario(
            self.regular_user, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    # There are no special bug supervisor rules for products.
    test_subscribe_link_feature_flag_on_user_no_bug_super = None
    test_subscribe_link_feature_flag_on_user_with_bug_super = None
    test_subscribe_link_feature_flag_off_bug_super = None
    test_subscribe_link_feature_flag_on_bug_super = None

    def test_subscribe_link_feature_flag_off_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, None)
        self.assertNotEqual(None, old_link)
        self.assertEqual(None, new_link)

    def test_subscribe_link_feature_flag_on_anonymous(self):
        old_link, new_link = self._create_scenario(
            ANONYMOUS, 'on')
        self.assertEqual(None, old_link)
        self.assertEqual(None, new_link)

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
        self.assertNotEqual(None, new_link)


class TestProductSeriesMilestoneViewStructSubs(
    TestProductMilestoneViewStructSubs):
    """Test structural subscriptions on the product series milestones."""

    def setUp(self):
        super(TestProductSeriesMilestoneViewStructSubs, self).setUp()
        self.productseries = self.factory.makeProductSeries()
        with person_logged_in(self.productseries.product.owner):
            self.productseries.product.official_malone = True
        self.regular_user = self.factory.makePerson()
        self.target = self.factory.makeMilestone(
            productseries=self.productseries)


def test_suite():
    """Return the `IStructuralSubscriptionTarget` TestSuite."""

    # Manually construct the test suite to avoid having tests from the base
    # class _TestStructSubs run.
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestProductViewStructSubs))
    suite.addTest(unittest.makeSuite(TestProductBugsStructSubs))
    suite.addTest(unittest.makeSuite(TestProductSeriesViewStructSubs))
    suite.addTest(unittest.makeSuite(TestProductSeriesBugsStructSubs))
    suite.addTest(unittest.makeSuite(TestProjectGroupViewStructSubs))
    suite.addTest(unittest.makeSuite(TestProjectGroupBugsStructSubs))
    suite.addTest(unittest.makeSuite(
        TestDistributionSourcePackageViewStructSubs))
    suite.addTest(unittest.makeSuite(
        TestDistributionSourcePackageBugsStructSubs))
    suite.addTest(unittest.makeSuite(TestDistroViewStructSubs))
    suite.addTest(unittest.makeSuite(TestDistroBugsStructSubs))
    suite.addTest(unittest.makeSuite(TestDistroMilestoneViewStructSubs))
    suite.addTest(unittest.makeSuite(TestProductMilestoneViewStructSubs))
    suite.addTest(unittest.makeSuite(
        TestProductSeriesMilestoneViewStructSubs))
    return suite
