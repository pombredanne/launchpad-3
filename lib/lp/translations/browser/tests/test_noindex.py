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
    """Test the inclusion of the meta "noindex,nofollow" directives.

    Subclasses using this mixin must set the following attributes:
    target - the pillar under test
    naked_translatable - the translatable object for the test, with the
    security proxy removed.  It may be the target or a subordinate object.
    (For example when testing a ProjectGroup the translatable is one of the
    products in the project group.)
    """

    layer = DatabaseFunctionalLayer

    def setUsage(self, usage):
        self.naked_translatable.translations_usage = usage

    def getView(self):
        view = create_initialized_view(
            self.target, '+translations',
            current_request=True, layer=TranslationsLayer)
        return view

    def getRenderedContents(self):
        """Return an initialized view's rendered contents."""
        # Using create_initialized_view for distroseries causes an error when
        # rendering the view due to the way the view is registered and menus
        # are adapted.  Getting the contents via a browser does work.
        url = canonical_url(self.target, rootsite='translations')
        browser = self.getUserBrowser(url)
        return browser.contents

    def getSoupAndRobots(self, usage):
        self.setUsage(usage)
        contents = self.getRenderedContents()
        soup = BeautifulSoup(contents)
        robots = soup.find('meta', attrs={'name': 'robots'})
        return soup, robots

    def verifyRobotsAreBlocked(self, usage):
        soup, robots = self.getSoupAndRobots(usage)
        self.assertIsNot(None, robots,
                         "Robot blocking meta information not present.")
        self.assertEqual('noindex,nofollow', robots['content'])
        expected = ('noindex', 'nofollow')
        actual = robots['content'].split(',')
        self.assertContentEqual(expected, actual)

    def verifyRobotsNotBlocked(self, usage):
        soup, robots = self.getSoupAndRobots(usage)
        self.assertIs(
            None, robots,
            "Robot blocking metadata present when it should not be.")

    def test_UNKNOWN_blocks_robots(self):
        self.verifyRobotsAreBlocked(ServiceUsage.UNKNOWN)

    def test_EXTERNAL_blocks_robots(self):
        self.verifyRobotsAreBlocked(ServiceUsage.EXTERNAL)

    def test_NOT_APPLICABLE_blocks_robots(self):
        self.verifyRobotsAreBlocked(ServiceUsage.NOT_APPLICABLE)

    def test_LAUNCHPAD_does_not_block_robots(self):
        self.verifyRobotsNotBlocked(ServiceUsage.LAUNCHPAD)


class TestRobotsProduct(BrowserTestCase, TestRobotsMixin):
    """Test noindex,nofollow for products."""

    def setUp(self):
        super(TestRobotsProduct, self).setUp()
        self.target = self.factory.makeProduct()
        self.factory.makePOTemplate(
            productseries=self.target.development_focus)
        self.naked_translatable = removeSecurityProxy(self.target)


class TestRobotsProjectGroup(BrowserTestCase, TestRobotsMixin):
    """Test noindex,nofollow for project groups."""

    def setUp(self):
        super(TestRobotsProjectGroup, self).setUp()
        self.target = self.factory.makeProject()
        self.product = self.factory.makeProduct()
        self.factory.makePOTemplate(
            productseries=self.product.development_focus)
        self.naked_translatable = removeSecurityProxy(self.product)
        self.naked_translatable.project = self.target


class TestRobotsProductSeries(BrowserTestCase, TestRobotsMixin):
    """Test noindex,nofollow for product series."""

    def setUp(self):
        super(TestRobotsProductSeries, self).setUp()
        self.product = self.factory.makeProduct()
        self.target = self.product.development_focus
        self.factory.makePOTemplate(
            productseries=self.target)
        self.naked_translatable = removeSecurityProxy(self.product)


class TestRobotsDistroSeries(BrowserTestCase, TestRobotsMixin):
    """Test noindex,nofollow for distro series."""

    def setUp(self):
        super(TestRobotsDistroSeries, self).setUp()
        self.owner = self.factory.makePerson()
        login_person(self.owner)
        self.distro = self.factory.makeDistribution(
            name="whobuntu", owner=self.owner)
        self.target = self.factory.makeDistroSeries(
            name="zephyr", distribution=self.distro)
        self.target.hide_all_translations = False
        new_sourcepackagename = self.factory.makeSourcePackageName()
        self.factory.makePOTemplate(
            distroseries=self.target,
            sourcepackagename=new_sourcepackagename)
        self.naked_translatable = removeSecurityProxy(self.distro)


class TestRobotsDistro(BrowserTestCase, TestRobotsMixin):
    """Test noindex,nofollow for distro."""

    def setUp(self):
        super(TestRobotsDistro, self).setUp()
        self.owner = self.factory.makePerson()
        login_person(self.owner)
        self.target = self.factory.makeDistribution(
            name="whobuntu", owner=self.owner)
        self.distroseries = self.factory.makeDistroSeries(
            name="zephyr", distribution=self.target)
        self.distroseries.hide_all_translations = False
        new_sourcepackagename = self.factory.makeSourcePackageName()
        self.factory.makePOTemplate(
            distroseries=self.distroseries,
            sourcepackagename=new_sourcepackagename)
        self.naked_translatable = removeSecurityProxy(self.target)
