# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=F0401,E1002

"""Tests for the source package recipe view classes and templates."""

__metaclass__ = type

import transaction

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.testing.pages import (
    extract_text, find_main_content, find_tags_by_class)
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadFunctionalLayer)
from lp.code.browser.sourcepackagerecipebuild import (
    SourcePackageRecipeBuildView)
from lp.code.interfaces.sourcepackagerecipe import MINIMAL_RECIPE_TEXT
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.model.processor import ProcessorFamily
from lp.testing import ANONYMOUS, BrowserTestCase, login, logout


class TestSourcePackageRecipeBuild(BrowserTestCase):
    """Create some sample data for recipe tests."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Provide useful defaults."""
        super(TestSourcePackageRecipeBuild, self).setUp()
        self.chef = self.factory.makePerson(
            displayname='Master Chef', name='chef', password='test')
        self.user = self.chef
        self.ppa = self.factory.makeArchive(
            displayname='Secret PPA', owner=self.chef, name='ppa')
        self.squirrel = self.factory.makeDistroSeries(
            displayname='Secret Squirrel', name='secret', version='100.04',
            distribution=self.ppa.distribution)
        self.squirrel.nominatedarchindep = self.squirrel.newArch(
            'i386', ProcessorFamily.get(1), False, self.chef,
            supports_virtualized=True)

    def makeRecipeBuild(self):
        """Create and return a specific recipe."""
        chocolate = self.factory.makeProduct(name='chocolate')
        cake_branch = self.factory.makeProductBranch(
            owner=self.chef, name='cake', product=chocolate)
        recipe = self.factory.makeSourcePackageRecipe(
            owner=self.chef, distroseries=self.squirrel, name=u'cake_recipe',
            description=u'This recipe builds a foo for disto bar, with my'
            ' Secret Squirrel changes.', branches=[cake_branch],
            daily_build_archive=self.ppa)
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe)
        return build

    def test_delete_build(self):
        """An admin can delete a build."""
        build = self.makeRecipeBuild()
        transaction.commit()
        build_url = canonical_url(build)
        recipe = build.recipe
        next_url = canonical_url(recipe)
        logout()

        browser = self.getUserBrowser(build_url, user=self.chef)
        browser.getLink('Delete build').click()

        browser.getControl('Delete build').click()

        self.assertEqual(
            browser.url,
            next_url)
        self.assertEqual(
            recipe.getBuilds().count(),
            0)

    def test_delete_build_cancel(self):
        """An admin can delete a build."""
        build = self.makeRecipeBuild()
        transaction.commit()
        build_url = canonical_url(build)
        logout()

        browser = self.getUserBrowser(build_url, user=self.chef)
        browser.getLink('Delete build').click()

        browser.getLink('Cancel').click()
        self.assertEqual(
            browser.url,
            build_url)

    def test_delete_build_not_admin(self):
        """No one but admins can delete a build."""
        build = self.makeRecipeBuild()
        transaction.commit()
        build_url = canonical_url(build)
        logout()

        browser = self.getUserBrowser(build_url, user=self.chef)
        browser.getLink('Delete build').click()
