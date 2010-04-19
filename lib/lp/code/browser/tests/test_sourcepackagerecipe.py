# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
# pylint: disable-msg=F0401

"""Tests for the source package recipe view classes and templates."""

__metaclass__ = type


from datetime import datetime
from textwrap import dedent
import re

from pytz import utc
from canonical.testing import DatabaseFunctionalLayer
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.testing.pages import extract_text, find_main_content
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.browser.sourcepackagerecipe import SourcePackageRecipeView
from lp.testing import (ANONYMOUS, login, TestCaseWithFactory)


class TestSourcePackageRecipeView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Provide useful defaults."""
        super(TestSourcePackageRecipeView, self).setUp()
        self.chef = self.factory.makePerson(
            displayname='Master Chef', name='chef', password='test')
        self.ppa = self.factory.makeArchive(
            displayname='Secret PPA', owner=self.chef)
        self.squirrel = self.factory.makeDistroSeries(
            displayname='Secret Squirrel', name='secret')

    def makeRecipe(self):
        """Create and return a specific recipe."""
        chocolate = self.factory.makeProduct(name='chocolate')
        cake_branch = self.factory.makeProductBranch(
            owner=self.chef, name='cake', product=chocolate)
        return self.factory.makeSourcePackageRecipe(
            None, self.chef, self.squirrel, None, u'cake_recipe',
            u'This recipe builds a foo for disto bar, with my Secret Squirrel'
            ' changes.', cake_branch)

    def getRecipeBrowser(self, recipe, view_name=None):
        """Return a browser for the specified recipe, opened as Chef."""
        login(ANONYMOUS)
        url = canonical_url(recipe, view_name=view_name)
        return self.getUserBrowser(url, self.chef)

    def getMainText(self, recipe, view_name=None):
        """Return the main text of a recipe page, as seen by Chef."""
        browser = self.getRecipeBrowser(recipe, view_name)
        return extract_text(find_main_content(browser.contents))

    def test_index(self):
        recipe = self.makeRecipe()
        build = removeSecurityProxy(self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, distroseries=self.squirrel, archive=self.ppa))
        build.buildstate = BuildStatus.FULLYBUILT
        build.datebuilt = datetime(2010, 03, 16, tzinfo=utc)
        pattern = re.compile(dedent("""\
            Master Chef
            Branches
            Description
            This recipe .*changes.
            Recipe information
            Owner:
            Master Chef
            Base branch:
            lp://dev/~chef/chocolate/cake
            Debian version:
            1.0
            Distribution series:
            Secret Squirrel
            Build records
            Status
            Time
            Distribution series
            Archive
            Successful build
            on 2010-03-16
            Secret Squirrel
            Secret PPA
            Request build\(s\)
            Recipe contents
            # bzr-builder format 0.2 deb-version 1.0
            lp://dev/~chef/chocolate/cake"""), re.S)
        main_text = self.getMainText(recipe)
        self.assertTrue(pattern.search(main_text), repr(main_text))

    def test_index_no_suitable_builders(self):
        recipe = self.makeRecipe()
        removeSecurityProxy(self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, distroseries=self.squirrel, archive=self.ppa))
        pattern = re.compile(dedent("""\
            Build records
            Status
            Time
            Distribution series
            Archive
            No suitable builders
            Secret Squirrel
            Secret PPA
            Request build\(s\)"""), re.S)
        main_text = self.getMainText(recipe)
        self.assertTrue(pattern.search(main_text), main_text)

    def makeBuildJob(self, recipe):
        """Return a build associated with a buildjob."""
        build = self.factory.makeSourcePackageRecipeBuild(
            recipe=recipe, distroseries=self.squirrel, archive=self.ppa )
        self.factory.makeSourcePackageRecipeBuildJob(recipe_build=build)
        return build

    def test_index_pending(self):
        """Test the listing of a pending build."""
        recipe = self.makeRecipe()
        self.makeBuildJob(recipe)
        self.factory.makeBuilder()
        pattern = re.compile(dedent("""\
            Build records
            Status
            Time
            Distribution series
            Archive
            Pending build
            in .*
            \(estimated\)
            Secret Squirrel
            Secret PPA
            Request build\(s\)
            Recipe contents"""), re.S)
        main_text = self.getMainText(recipe)
        self.assertTrue(pattern.search(main_text), main_text)

    def test_builds(self):
        """Ensure SourcePackageRecipeView.builds is as described."""
        recipe = self.makeRecipe()
        build1 = self.makeBuildJob(recipe=recipe)
        build2 = self.makeBuildJob(recipe=recipe)
        build3 = self.makeBuildJob(recipe=recipe)
        build4 = self.makeBuildJob(recipe=recipe)
        build5 = self.makeBuildJob(recipe=recipe)
        build6 = self.makeBuildJob(recipe=recipe)
        view = SourcePackageRecipeView(recipe, None)
        self.assertEqual(
            set([build1, build2, build3, build4, build5, build6]),
            set(view.builds))
        def set_day(build, day):
            removeSecurityProxy(build).datebuilt = datetime(
                2010, 03, day, tzinfo=utc)
        set_day(build1, 16)
        set_day(build2, 15)
        # When there are 4+ pending builds, only the the most
        # recently-completed build is returned (i.e. build1, not build2)
        self.assertEqual(
            set([build1, build3, build4, build5, build6]),
            set(view.builds))
        set_day(build3, 14)
        set_day(build4, 13)
        set_day(build5, 12)
        set_day(build6, 11)
        self.assertEqual(
            [build5, build4, build3, build2, build1], view.builds)

    def test_request_builds_page(self):
        """Ensure the +request-builds page is sane."""
        recipe = self.makeRecipe()
        text = self.getMainText(recipe, '+request-builds')
        self.assertEqual(dedent(u"""\
            Request builds for cake_recipe
            Master Chef
            Branches
            Request builds for cake_recipe
            Archive:
            Secret PPA (chef/ppa)
            Distribution series:
            Warty
            Hoary
            Six
            7.0
            Woody
            Sarge
            Guada2005
            Secret Squirrel
            or
            Cancel"""), text)

    def test_request_builds_action(self):
        """Requesting a build creates pending builds."""
        recipe = self.makeRecipe()
        browser = self.getRecipeBrowser(recipe, '+request-builds')
        browser.getControl('Woody').click()
        browser.getControl('Request builds').click()
        build_distros = [
            build.distroseries.displayname for build in
            recipe.getBuilds(True)]
        build_distros.sort()
        # Secret Squirrel is checked by default.
        self.assertEqual(['Secret Squirrel', 'Woody'], build_distros)
