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
from canonical.launchpad.testing.pages import first_tag_by_class
from canonical.testing.layers import DatabaseFunctionalLayer

from lp.registry.interfaces.person import IPersonSet
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


class _TestResultsMixin:
    """Mixin to provide common result checking helper methods."""

    @property
    def old_link(self):
        return first_tag_by_class(
            self.contents, 'menu-link-subscribe')

    @property
    def new_subscribe_link(self):
        return first_tag_by_class(
            self.contents, 'menu-link-subscribe_to_bug_mail')

    @property
    def new_edit_link(self):
        return first_tag_by_class(
            self.contents, 'menu-link-edit_bug_mail')

    def assertOldLinkMissing(self):
        self.assertEqual(
            None, self.old_link,
            "Found unexpected link: %s" % self.old_link)

    def assertOldLinkPresent(self):
        self.assertNotEqual(
            None, self.old_link,
            "Expected +subscribe link missing")

    def assertNewLinksMissing(self):
        self.assertEqual(
            None, self.new_subscribe_link,
            "Found unexpected link: %s" % self.new_subscribe_link)
        self.assertEqual(
            None, self.new_edit_link,
            "Found unexpected link: %s" % self.new_edit_link)

    def assertNewLinksPresent(self):
        self.assertNotEqual(
            None, self.new_subscribe_link,
            "Expected subscribe_to_bug_mail link missing")
        self.assertNotEqual(
            None, self.new_edit_link,
            "Expected edit_bug_mail link missing")
        # Ensure the LP.cache has been populated.
        self.assertTrue("LP.cache['administratedTeams']" in self.contents)
        # And that the call to setup the subscription is in the HTML.  A
        # windmill test is required to ensure that the call actually
        # succeeded, by checking the link class for 'js-action'.
        setup = ("""module.setup({content_box: """
                 """"#structural-subscription-content-box"});""")
        self.assertTrue(setup in self.contents)


class _TestStructSubs(TestCaseWithFactory, _TestResultsMixin):
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

    def create_view(self, user):
        return create_initialized_view(
            self.target, self.view, principal=user,
            rootsite=self.rootsite, current_request=False)

    def test_subscribe_link_feature_flag_off_owner(self):
        self._create_scenario(self.target.owner, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_owner(self):
        # Test the new subscription link.
        self._create_scenario(self.target.owner, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_user(self):
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user(self):
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_anonymous(self):
        self._create_scenario(ANONYMOUS, None)
        # The old subscribe link is actually shown to anonymous users but the
        # behavior has changed with the new link.
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_anonymous(self):
        self._create_scenario(ANONYMOUS, 'on')
        # The subscribe link is not shown to anonymous.
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()


class ProductView(_TestStructSubs):
    """Test structural subscriptions on the product view."""

    rootsite = None
    view = '+index'

    def setUp(self):
        super(ProductView, self).setUp()
        self.target = self.factory.makeProduct(official_malone=True)


class ProductBugs(ProductView):
    """Test structural subscriptions on the product bugs view."""

    rootsite = 'bugs'
    view = '+bugs-index'


class ProjectGroupView(_TestStructSubs):
    """Test structural subscriptions on the project group view."""

    rootsite = None
    view = '+index'

    def setUp(self):
        super(ProjectGroupView, self).setUp()
        self.target = self.factory.makeProject()
        self.factory.makeProduct(
            project=self.target, official_malone=True)


class ProjectGroupBugs(ProjectGroupView):
    """Test structural subscriptions on the project group bugs view."""

    rootsite = 'bugs'
    view = '+bugs'


class ProductSeriesView(_TestStructSubs):
    """Test structural subscriptions on the product series view."""

    rootsite = None
    view = '+index'

    def setUp(self):
        super(ProductSeriesView, self).setUp()
        product = self.factory.makeProduct(official_malone=True)
        self.target = self.factory.makeProductSeries(product=product)


class ProductSeriesBugs(ProductSeriesView):
    """Test structural subscriptions on the product series bugs view."""

    rootsite = 'bugs'
    view = '+bugs-index'

    def setUp(self):
        super(ProductSeriesBugs, self).setUp()
        with person_logged_in(self.target.product.owner):
            self.target.product.official_malone = True


class DistributionSourcePackageView(_TestStructSubs):
    """Test structural subscriptions on the distro src pkg view."""

    rootsite = None
    view = '+index'

    def setUp(self):
        super(DistributionSourcePackageView, self).setUp()
        distro = self.factory.makeDistribution()
        with person_logged_in(distro.owner):
            distro.official_malone = True
        self.target = self.factory.makeDistributionSourcePackage(
            distribution=distro)
        self.regular_user = self.factory.makePerson()

    # DistributionSourcePackages do not have owners.
    test_subscribe_link_feature_flag_off_owner = None
    test_subscribe_link_feature_flag_on_owner = None


class DistributionSourcePackageBugs(DistributionSourcePackageView):
    """Test structural subscriptions on the distro src pkg bugs view."""

    rootsite = 'bugs'
    view = '+bugs'


class DistroView(BrowserTestCase, _TestResultsMixin):
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
        super(DistroView, self).setUp()
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

    @property
    def old_link(self):
        href = canonical_url(
            self.target, rootsite=self.rootsite,
            view_name='+subscribe')
        soup = BeautifulSoup(self.contents)
        return soup.find('a', href=href)

    def test_subscribe_link_feature_flag_off_owner(self):
        self._create_scenario(self.target.owner, None)
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_owner(self):
        self._create_scenario(self.target.owner, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_user(self):
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user_no_bug_super(self):
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_on_user_with_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            supervisor = self.factory.makePerson()
            self.target.setBugSupervisor(
                supervisor, admin)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_anonymous(self):
        self._create_scenario(ANONYMOUS, None)
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_anonymous(self):
        self._create_scenario(ANONYMOUS, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, None)
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()


class DistroBugs(DistroView):
    """Test structural subscriptions on the distro bugs view."""

    rootsite = 'bugs'
    view = '+bugs-index'

    def test_subscribe_link_feature_flag_off_owner(self):
        self._create_scenario(self.target.owner, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_owner(self):
        self._create_scenario(self.target.owner, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_user(self):
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user_no_bug_super(self):
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_on_user_with_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            supervisor = self.factory.makePerson()
            self.target.setBugSupervisor(
                supervisor, admin)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_anonymous(self):
        self._create_scenario(ANONYMOUS, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_anonymous(self):
        self._create_scenario(ANONYMOUS, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_admin(self):
        from lp.testing.sampledata import ADMIN_EMAIL
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()


class DistroMilestoneView(DistroView):
    """Test structural subscriptions on the distro milestones."""

    def setUp(self):
        super(DistroMilestoneView, self).setUp()
        self.distro = self.target
        self.target = self.factory.makeMilestone(distribution=self.distro)

    def test_subscribe_link_feature_flag_off_owner(self):
        self._create_scenario(self.distro.owner, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_owner(self):
        self._create_scenario(self.distro.owner, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_user(self):
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user_no_bug_super(self):
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_on_user_with_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            supervisor = self.factory.makePerson()
            self.distro.setBugSupervisor(
                supervisor, admin)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_anonymous(self):
        self._create_scenario(ANONYMOUS, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_anonymous(self):
        self._create_scenario(ANONYMOUS, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.distro.setBugSupervisor(
                self.regular_user, admin)
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.distro.setBugSupervisor(
                self.regular_user, admin)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_admin(self):
        from lp.testing.sampledata import ADMIN_EMAIL
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()


class ProductMilestoneView(DistroView):
    """Test structural subscriptions on the product milestones."""

    def setUp(self):
        super(ProductMilestoneView, self).setUp()
        self.product = self.factory.makeProduct()
        with person_logged_in(self.product.owner):
            self.product.official_malone = True
        self.regular_user = self.factory.makePerson()
        self.target = self.factory.makeMilestone(product=self.product)

    def test_subscribe_link_feature_flag_off_owner(self):
        self._create_scenario(self.product.owner, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_owner(self):
        self._create_scenario(self.product.owner, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()

    def test_subscribe_link_feature_flag_off_user(self):
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    # There are no special bug supervisor rules for products.
    test_subscribe_link_feature_flag_on_user_no_bug_super = None
    test_subscribe_link_feature_flag_on_user_with_bug_super = None
    test_subscribe_link_feature_flag_off_bug_super = None
    test_subscribe_link_feature_flag_on_bug_super = None

    def test_subscribe_link_feature_flag_off_anonymous(self):
        self._create_scenario(ANONYMOUS, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_anonymous(self):
        self._create_scenario(ANONYMOUS, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, None)
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_admin(self):
        from lp.testing.sampledata import ADMIN_EMAIL
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksPresent()


class ProductSeriesMilestoneView(ProductMilestoneView):
    """Test structural subscriptions on the product series milestones."""

    def setUp(self):
        super(ProductSeriesMilestoneView, self).setUp()
        self.productseries = self.factory.makeProductSeries()
        with person_logged_in(self.productseries.product.owner):
            self.productseries.product.official_malone = True
        self.regular_user = self.factory.makePerson()
        self.target = self.factory.makeMilestone(
            productseries=self.productseries)

# Tests for when the IStructuralSubscriptionTarget does not use Launchpad for
# bug tracking.  In those cases the links should not be shown.

class _DoesNotUseLP(ProductView):
    """Test structural subscriptions on the product view."""

    def setUp(self):
        super(_DoesNotUseLP, self).setUp()
        self.target = self.factory.makeProduct(official_malone=False)

    def test_subscribe_link_feature_flag_on_owner(self):
        # Test the new subscription link.
        self._create_scenario(self.target.owner, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user(self):
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_anonymous(self):
        self._create_scenario(ANONYMOUS, 'on')
        # The subscribe link is not shown to anonymous.
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()


class ProductDoesNotUseLPView(_DoesNotUseLP):

    def test_subscribe_link_no_bugtracker_parent_bugtracker(self):
        # If there is no bugtracker, do not render links, even if the
        # parent has a bugtracker (see bug 770287).
        project = self.factory.makeProject()
        with person_logged_in(self.target.owner):
            self.target.project = project
        another_product = self.factory.makeProduct(
            project=project, official_malone=True)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()


class ProductDoesNotUseLPBugs(ProductDoesNotUseLPView):
    """Test structural subscriptions on the product bugs view."""

    rootsite = 'bugs'
    view = '+bugs-index'

    def test_subscribe_link_feature_flag_off_owner(self):
        self._create_scenario(self.target.owner, None)
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_user(self):
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_anonymous(self):
        self._create_scenario(ANONYMOUS, None)
        # The old subscribe link is actually shown to anonymous users but the
        # behavior has changed with the new link.
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()


class ProjectGroupDoesNotUseLPView(_DoesNotUseLP):
    """Test structural subscriptions on the project group view."""

    rootsite = None
    view = '+index'

    def setUp(self):
        super(ProjectGroupDoesNotUseLPView, self).setUp()
        self.target = self.factory.makeProject()
        self.factory.makeProduct(
            project=self.target, official_malone=False)


class ProjectGroupDoesNotUseLPBugs(ProductDoesNotUseLPBugs):
    """Test structural subscriptions on the project group bugs view."""

    rootsite = 'bugs'
    view = '+bugs'

    def setUp(self):
        super(ProjectGroupDoesNotUseLPBugs, self).setUp()
        self.target = self.factory.makeProject()
        self.factory.makeProduct(
            project=self.target, official_malone=False)

    test_subscribe_link_no_bugtracker_parent_bugtracker = None


class ProductSeriesDoesNotUseLPView(_DoesNotUseLP):

    def setUp(self):
        super(ProductSeriesDoesNotUseLPView, self).setUp()
        product = self.factory.makeProduct(official_malone=False)
        self.target = self.factory.makeProductSeries(product=product)


class ProductSeriesDoesNotUseLPBugs(_DoesNotUseLP):

    def setUp(self):
        super(ProductSeriesDoesNotUseLPBugs, self).setUp()
        product = self.factory.makeProduct(official_malone=False)
        self.target = self.factory.makeProductSeries(product=product)


class DistributionSourcePackageDoesNotUseLPView(_DoesNotUseLP):
    """Test structural subscriptions on the distro src pkg view."""

    def setUp(self):
        super(DistributionSourcePackageDoesNotUseLPView, self).setUp()
        distro = self.factory.makeDistribution()
        self.target = self.factory.makeDistributionSourcePackage(
            distribution=distro)
        self.regular_user = self.factory.makePerson()

    # DistributionSourcePackages do not have owners.
    test_subscribe_link_feature_flag_off_owner = None
    test_subscribe_link_feature_flag_on_owner = None


class DistributionSourcePackageDoesNotUseLPBugs(ProductDoesNotUseLPBugs):
    """Test structural subscriptions on the distro src pkg bugs view."""

    view = '+bugs'

    # DistributionSourcePackages do not have owners.
    test_subscribe_link_feature_flag_off_owner = None
    test_subscribe_link_feature_flag_on_owner = None


class DistroDoesNotUseLPView(DistroView):

    def setUp(self):
        super(DistroDoesNotUseLPView, self).setUp()
        self.target = self.factory.makeDistribution()
        self.regular_user = self.factory.makePerson()

    def test_subscribe_link_feature_flag_on_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.target.setBugSupervisor(
                self.regular_user, admin)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user_no_bug_super(self):
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_owner(self):
        # Test the new subscription link.
        self._create_scenario(self.target.owner, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user(self):
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_anonymous(self):
        self._create_scenario(ANONYMOUS, 'on')
        # The subscribe link is not shown to anonymous.
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()


class DistroDoesNotUseLPBugs(DistroDoesNotUseLPView):
    rootsite = 'bugs'
    view = '+bugs-index'

    def test_subscribe_link_feature_flag_off_owner(self):
        self._create_scenario(self.target.owner, None)
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_user(self):
        self._create_scenario(self.regular_user, None)
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_anonymous(self):
        self._create_scenario(ANONYMOUS, None)
        # The old subscribe link is actually shown to anonymous users but the
        # behavior has changed with the new link.
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()


class DistroMilestoneDoesNotUseLPView(DistroMilestoneView):

    def setUp(self):
        super(DistroMilestoneDoesNotUseLPView, self).setUp()
        with person_logged_in(self.distro.owner):
            self.distro.official_malone = False

    def test_subscribe_link_feature_flag_on_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            self.distro.setBugSupervisor(
                self.regular_user, admin)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user_no_bug_super(self):
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_owner(self):
        # Test the new subscription link.
        self._create_scenario(self.distro.owner, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user(self):
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_anonymous(self):
        self._create_scenario(ANONYMOUS, 'on')
        # The subscribe link is not shown to anonymous.
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_user_with_bug_super(self):
        with celebrity_logged_in('admin'):
            admin = getUtility(ILaunchBag).user
            supervisor = self.factory.makePerson()
            self.distro.setBugSupervisor(
                supervisor, admin)
        self._create_scenario(self.regular_user, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()


class ProductMilestoneDoesNotUseLPView(ProductMilestoneView):

    def setUp(self):
        BrowserTestCase.setUp(self)
        self.product = self.factory.makeProduct()
        with person_logged_in(self.product.owner):
            self.product.official_malone = False
        self.target = self.factory.makeMilestone(
            name='1.0', product=self.product)
        self.regular_user = self.factory.makePerson()

    def test_subscribe_link_feature_flag_off_owner(self):
        self._create_scenario(self.product.owner, None)
        # The presence of the old link is certainly a mistake since the
        # product does not use Launchpad for bug tracking.
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_user(self):
        self._create_scenario(self.regular_user, None)
        # The presence of the old link is certainly a mistake since the
        # product does not use Launchpad for bug tracking.
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_anonymous(self):
        self._create_scenario(ANONYMOUS, None)
        # The presence of the old link is certainly a mistake since the
        # product does not use Launchpad for bug tracking.
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_off_admin(self):
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, None)
        # The presence of the old link is certainly a mistake since the
        # product does not use Launchpad for bug tracking.
        self.assertOldLinkPresent()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_admin(self):
        from lp.testing.sampledata import ADMIN_EMAIL
        admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self._create_scenario(admin, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()

    def test_subscribe_link_feature_flag_on_owner(self):
        self._create_scenario(self.product.owner, 'on')
        self.assertOldLinkMissing()
        self.assertNewLinksMissing()


class CustomTestLoader(unittest.TestLoader):
    """A test loader that avoids running tests from a base class."""

    def getTestCaseNames(self, testCaseClass):
        # If we're asked about which tests to run for _TestStructSubs, reply
        # with an empty list.
        if testCaseClass is _TestStructSubs:
            return []
        else:
            return super(CustomTestLoader, self).getTestCaseNames(
                testCaseClass)


def test_suite():
    """Return the `IStructuralSubscriptionTarget` TestSuite."""
    return CustomTestLoader().loadTestsFromName(__name__)
