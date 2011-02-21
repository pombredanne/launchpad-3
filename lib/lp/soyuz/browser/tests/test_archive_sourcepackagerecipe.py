# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ArchivePackagesView, with relation to source package
recipes."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import LaunchpadFunctionalLayer
from canonical.launchpad.webapp.publisher import canonical_url

from lp.registry.interfaces.person import IPersonSet
from lp.soyuz.enums import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class TestArchivePackagesViewSourcePackageRecipe(BrowserTestCase):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestArchivePackagesViewSourcePackageRecipe, self).setUp()
        self.admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        # Create everything we need to create builds, such as a
        # DistroArchSeries and a builder.
        self.pf = self.factory.makeProcessorFamily()
        pf_proc = self.pf.addProcessor(self.factory.getUniqueString(), '', '')
        self.distroseries = self.factory.makeDistroSeries()
        self.das = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, processorfamily=self.pf,
            supports_virtualized=True)
        self.archive = self.factory.makeArchive(
            distribution=self.distroseries.distribution)
        with person_logged_in(self.admin):
            self.publisher = SoyuzTestPublisher()
            self.publisher.prepareBreezyAutotest()
            self.distroseries.nominatedarchindep = self.das
            self.publisher.addFakeChroots(distroseries=self.distroseries)
            self.builder = self.factory.makeBuilder(processor=pf_proc)

    def test_view_with_source_package_recipe(self):
        # When a SourcePackageRelease is linked to a
        # SourcePackageRecipeBuild, the view shows which recipe was
        # responsible for creating the SPR.
        sprb = self.factory.makeSourcePackageRecipeBuild(
            archive=self.archive)
        recipe = sprb.recipe
        spph = self.publisher.getPubSource(
            archive=self.archive, status=PackagePublishingStatus.PUBLISHED)
        spph.sourcepackagerelease.source_package_recipe_build = sprb
        expected_contents = 'Built by recipe <a href="%s">%s</a> for %s' % (
            canonical_url(recipe), recipe.name, recipe.owner.displayname)
        browser = self.getViewBrowser(self.archive, '+packages')
        browser.getLink('Show details').click()
        self.assertIn(expected_contents, browser.contents)

    def test_view_without_source_package_recipe(self):
        # And if a SourcePackageRelease is not linked, there is no sign of it
        # in the view.
        with person_logged_in(self.admin):
            self.publisher.getPubBinaries(
                archive=self.archive,
                status=PackagePublishingStatus.PUBLISHED)
        browser = self.getViewBrowser(self.archive, '+packages')
        browser.getLink('Show details').click()
        self.assertNotIn('Built by recipe', browser.contents)
