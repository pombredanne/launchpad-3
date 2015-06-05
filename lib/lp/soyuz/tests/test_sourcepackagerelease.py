# -*- coding: utf-8 -*-
# NOTE: The first line above must stay first; do not move the copyright
# notice to the top.  See http://www.python.org/dev/peps/pep-0263/.
#
# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test SourcePackageRelease."""

__metaclass__ = type

from textwrap import dedent

import transaction

from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadFunctionalLayer


class TestSourcePackageRelease(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_uploader_no_uploader(self):
        spr = self.factory.makeSourcePackageRelease()
        self.assertIs(None, spr.uploader)

    def test___repr__(self):
        spr = self.factory.makeSourcePackageRelease()
        expected_repr = ('<{cls} {pkg_name} (id: {id}, '
                         'version: {version})>').format(
                             cls=spr.__class__.__name__, pkg_name=spr.name,
                             id=spr.id, version=spr.version)
        self.assertEqual(expected_repr, repr(spr))

    def test_uploader_dsc_package(self):
        owner = self.factory.makePerson()
        key = self.factory.makeGPGKey(owner)
        spr = self.factory.makeSourcePackageRelease(dscsigningkey=key)
        self.assertEqual(owner, spr.uploader)

    def test_uploader_recipe(self):
        recipe_build = self.factory.makeSourcePackageRecipeBuild()
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

    def test_aggregate_changelog(self):
        # If since_version is passed the "changelog" entry returned
        # should contain the changelogs for all releases *since*
        # that version and up to and including the context SPR.
        changelog = self.factory.makeChangelog(
            spn="foo", versions=["1.3",  "1.2",  "1.1",  "1.0"])
        expected_changelog = dedent(u"""\
            foo (1.3) unstable; urgency=low

              * 1.3.

            foo (1.2) unstable; urgency=low

              * 1.2.

            foo (1.1) unstable; urgency=low

              * 1.1.""")
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename="foo", version="1.3", changelog=changelog)
        transaction.commit()  # Yay, librarian.

        observed = spph.sourcepackagerelease.aggregate_changelog(
            since_version="1.0")
        self.assertEqual(expected_changelog, observed)

    def test_aggregate_changelog_invalid_utf8(self):
        # aggregate_changelog copes with invalid UTF-8.
        changelog_main = dedent(u"""\
            foo (1.0) unstable; urgency=low

              * 1.0 (héllo).""").encode("ISO-8859-1")
        changelog_trailer = (
            u" -- Føo Bær <foo@example.com>  "
            u"Tue, 01 Jan 1970 01:50:41 +0000").encode("ISO-8859-1")
        changelog_text = changelog_main + b"\n\n" + changelog_trailer
        changelog = self.factory.makeLibraryFileAlias(content=changelog_text)
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename="foo", version="1.0", changelog=changelog)
        transaction.commit()
        observed = spph.sourcepackagerelease.aggregate_changelog(
            since_version=None)
        self.assertEqual(changelog_main.decode("UTF-8", "replace"), observed)
