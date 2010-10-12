# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from BeautifulSoup import BeautifulSoup
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.enums import ServiceUsage
from lp.testing import (
    BrowserTestCase,
    login_person,
    )
from lp.testing.views import create_initialized_view
from lp.translations.publisher import TranslationsLayer


class TestRobotsMixin:
    """Test the inclusion of the meta "noindex,nofollow" directives."""

    layer = DatabaseFunctionalLayer

    def set_usage(self, usage):
        self.naked_translatable.translations_usage = usage

    def get_view(self):
        """Return an initialized view's rendered contents."""
        raise NotImplementedError

    def get_rendered_contents(self):
        """Return an initialized view's rendered contents."""
        url = canonical_url(self.target, rootsite='translations')
        browser = self.getUserBrowser(url)
        return browser.contents

    @property
    def target(self):
        """The target of this test.

        Must be overridden.
        """
        raise NotImplementedError

    @property
    def naked_translatable(self):
        """The actual object that is translatable, not necessarily the target.

        For instance, for a ProjectGroup the translatable is the product.
        Must be overridden.
        """
        raise NotImplementedError

    def get_soup_and_robots(self, usage):
        self.set_usage(usage)
        contents = self.get_rendered_contents()
        soup = BeautifulSoup(contents)
        robots = soup.find('meta', attrs={'name': 'robots'})
        return soup, robots

    def verify_robots_are_blocked(self, usage):
        soup, robots = self.get_soup_and_robots(usage)
        self.assertIsNot(None, robots,
                         "Robot blocking meta information not present.")
        self.assertEqual('noindex,nofollow', robots['content'])

    def verify_robots_not_blocked(self, usage):
        soup, robots = self.get_soup_and_robots(usage)
        self.assertIs(
            None, robots,
            "Robot blocking metadata present when it should not be.")

    def test_UNKNOWN_blocks_robots(self):
        self.verify_robots_are_blocked(ServiceUsage.UNKNOWN)

    def test_EXTERNAL_blocks_robots(self):
        self.verify_robots_are_blocked(ServiceUsage.EXTERNAL)

    def test_NOT_APPLICABLE_blocks_robots(self):
        self.verify_robots_are_blocked(ServiceUsage.NOT_APPLICABLE)

    def test_LAUNCHPAD_does_not_block_robots(self):
        self.verify_robots_not_blocked(ServiceUsage.LAUNCHPAD)


class TestRobotsProduct(BrowserTestCase, TestRobotsMixin):
    """Test noindex,nofollow for products."""

    def setUp(self):
        super(TestRobotsProduct, self).setUp()
        self.product = self.factory.makeProduct()
        self.factory.makePOTemplate(
            productseries=self.product.development_focus)

    @property
    def target(self):
        return self.product

    @property
    def naked_translatable(self):
        return removeSecurityProxy(self.product)

    def get_view(self):
        view = create_initialized_view(
            self.target, '+translations',
            current_request=True, layer=TranslationsLayer)
        return view


class TestRobotsProjectGroup(TestRobotsProduct):
    """Test noindex,nofollow for project groups."""

    def setUp(self):
        super(TestRobotsProjectGroup, self).setUp()
        self.projectgroup = self.factory.makeProject()
        self.product = self.factory.makeProduct()
        self.factory.makePOTemplate(
            productseries=self.product.development_focus)
        self.naked_translatable.project = self.projectgroup

    @property
    def target(self):
        return self.projectgroup

    def test_has_translatables_true(self):
        self.set_usage(ServiceUsage.LAUNCHPAD)
        view = self.get_view()
        self.assertTrue(view.has_translatables)

    def test_has_translatables_false(self):
        self.set_usage(ServiceUsage.UNKNOWN)
        view = self.get_view()
        self.assertFalse(view.has_translatables)


class TestRobotsProductSeries(TestRobotsProduct):
    """Test noindex,nofollow for product series."""

    def setUp(self):
        super(TestRobotsProductSeries, self).setUp()
        self.product = self.factory.makeProduct()
        self.productseries = self.product.development_focus
        self.factory.makePOTemplate(
            productseries=self.productseries)

    @property
    def target(self):
        return self.productseries


class TestRobotsDistroSeries(BrowserTestCase, TestRobotsMixin):
    """Test noindex,nofollow for distro series."""

    def setUp(self):
        super(TestRobotsDistroSeries, self).setUp()
        self.owner = self.factory.makePerson()
        login_person(self.owner)
        self.distro = self.factory.makeDistribution(
            name="whobuntu", owner=self.owner)
        self.distroseries = self.factory.makeDistroSeries(
            name="zephyr", distribution=self.distro)
        self.distroseries.hide_all_translations = False
        new_sourcepackagename = self.factory.makeSourcePackageName()
        self.factory.makePOTemplate(
            distroseries=self.distroseries,
            sourcepackagename=new_sourcepackagename)

    @property
    def target(self):
        return self.distroseries

    @property
    def naked_translatable(self):
        return removeSecurityProxy(self.distro)

    def get_view(self):
        view = create_initialized_view(
            self.target, '+translations',
            layer=TranslationsLayer,
            rootsite='translations',
            current_request=True)
        return view

    def get_rendered_contents(self):
        # Using create_initialized_view for distroseries causes an error when
        # rendering the view due to the way the view is registered and menus
        # are adapted.  Getting the contents via a browser does work.
        url = canonical_url(self.target, rootsite='translations')
        browser = self.getUserBrowser(url)
        return browser.contents

    def test_LAUNCHPAD_does_not_block_robots(self):
        self.verify_robots_not_blocked(ServiceUsage.LAUNCHPAD)


class TestRobotsDistro(TestRobotsDistroSeries):
    """Test noindex,nofollow for distro."""

    def setUp(self):
        super(TestRobotsDistroSeries, self).setUp()
        self.owner = self.factory.makePerson()
        login_person(self.owner)
        self.distro = self.factory.makeDistribution(
            name="whobuntu", owner=self.owner)
        self.distroseries = self.factory.makeDistroSeries(
            name="zephyr", distribution=self.distro)
        self.distroseries.hide_all_translations = False
        new_sourcepackagename = self.factory.makeSourcePackageName()
        self.factory.makePOTemplate(
            distroseries=self.distroseries,
            sourcepackagename=new_sourcepackagename)

    @property
    def target(self):
        return self.distro

    @property
    def naked_translatable(self):
        return removeSecurityProxy(self.distro)
