# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test SourcePackageRelease."""

__metaclass__ = type

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestSourcePackageRelease(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_uploader_no_uploader(self):
        spr = self.factory.makeSourcePackageRelease()
        self.assertIs(None, spr.uploader)

    def test_uploader_dsc_package(self):
        owner = self.factory.makePerson()
        key = self.factory.makeGPGKey(owner)
        spr = self.factory.makeSourcePackageRelease(dscsigningkey=key)
        self.assertEqual(owner, spr.uploader)

    def test_uploader_recipe(self):
        recipe_build = self.factory.makeSourcePackageRecipeBuild()
        recipe = recipe_build.recipe
        spr = self.factory.makeSourcePackageRelease(
            source_package_recipe_build=recipe_build)
        self.assertEqual(recipe_build.requester, spr.uploader)

    def test_user_defined_fields(self):
        release = self.factory.makeSourcePackageRelease(
                user_defined_fields=[
                    ("Python-Version", ">= 2.4"),
                    ("Other", "Bla")])
        self.assertEquals([
            ["Python-Version", ">= 2.4"],
            ["Other", "Bla"]], release.user_defined_fields)

    def test_homepage_default(self):
        # By default, no homepage is set.
        spr = self.factory.makeSourcePackageRelease()
        self.assertEquals(None, spr.homepage)

    def test_homepage_empty(self):
        # The homepage field can be empty.
        spr = self.factory.makeSourcePackageRelease(homepage="")
        self.assertEquals("", spr.homepage)

    def test_homepage_set_invalid(self):
        # As the homepage field is inherited from the DSCFile, the URL
        # does not have to be valid.
        spr = self.factory.makeSourcePackageRelease(homepage="<invalid<url")
        self.assertEquals("<invalid<url", spr.homepage)
