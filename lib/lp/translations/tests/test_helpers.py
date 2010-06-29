# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing import ZopelessDatabaseLayer

from lp.testing import TestCaseWithFactory

from lp.translations.tests.helpers import (
    make_translationmessage,
    get_all_important_translations)


class TestTranslationMessageHelpers(TestCaseWithFactory):
    """Test discovery of translation suggestions."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestTranslationMessageHelpers, self).setUp()
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        sharing_series = self.factory.makeDistroRelease(distribution=ubuntu)
        sourcepackagename = self.factory.makeSourcePackageName()
        potemplate = self.factory.makePOTemplate(
            distroseries=ubuntu.currentseries,
            sourcepackagename=sourcepackagename)
        self.pofile = self.factory.makePOFile('sr', potemplate=potemplate)
        self.potmsgset = self.factory.makePOTMsgSet(potemplate=potemplate,
                                                    sequence=1)

        # A POFile in a different context from self.pofile.
        self.other_pofile = self.factory.makePOFile(
            language_code=self.pofile.language.code,
            variant=self.pofile.variant)

    def test_make_translationmessage(self):
        translations = [u"testing"]
        tm = make_translationmessage(self.factory, pofile=self.pofile,
                                     potmsgset=self.potmsgset,
                                     translations=translations)
        self.assertEquals(translations, tm.translations)

    def test_get_all_important_translations(self):
        current_shared, current_diverged, other, divergences = (
            get_all_important_translations(self.pofile, self.potmsgset))
        self.assertIs(None, current_shared)
        self.assertIs(None, current_diverged)
        self.assertIs(None, other)
        self.assertEquals([], divergences)

    def test_get_all_important_translations_current_shared(self):
        tm = make_translationmessage(
            self.factory, pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=False)
        current_shared, current_diverged, other, divergences = (
            get_all_important_translations(self.pofile, self.potmsgset))
        self.assertEquals(tm, current_shared)
        self.assertIs(None, current_diverged)
        self.assertIs(None, other)
        self.assertEquals([], divergences)

    def test_get_all_important_translations_current_both(self):
        tm = make_translationmessage(
            self.factory, pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=True, diverged=False)
        current_shared, current_diverged, other, divergences = (
            get_all_important_translations(self.pofile, self.potmsgset))
        self.assertEquals(tm, current_shared)
        self.assertIs(None, current_diverged)
        self.assertEquals(tm, other)
        self.assertEquals([], divergences)

    def test_get_all_important_translations_current_both_same(self):
        tm = make_translationmessage(
            self.factory, pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=True, diverged=False)
        current_shared, current_diverged, other, divergences = (
            get_all_important_translations(self.pofile, self.potmsgset))
        self.assertEquals(tm, current_shared)
        self.assertIs(None, current_diverged)
        self.assertEquals(tm, other)
        self.assertEquals([], divergences)

    def test_get_all_important_translations_current_two_different(self):
        tm_this = make_translationmessage(
            self.factory, pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=False)
        tm_other = make_translationmessage(
            self.factory, pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=False, upstream=True, diverged=False)
        current_shared, current_diverged, other, divergences = (
            get_all_important_translations(self.pofile, self.potmsgset))
        self.assertEquals(tm_this, current_shared)
        self.assertIs(None, current_diverged)
        self.assertEquals(tm_other, other)
        self.assertEquals([], divergences)

    def test_get_all_important_translations_current_three_different(self):
        tm_this = make_translationmessage(
            self.factory, pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=False)
        tm_other = make_translationmessage(
            self.factory, pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=False, upstream=True, diverged=False)
        tm_diverged = make_translationmessage(
            self.factory, pofile=self.pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=True)
        current_shared, current_diverged, other, divergences = (
            get_all_important_translations(self.pofile, self.potmsgset))
        self.assertEquals(tm_this, current_shared)
        self.assertEquals(tm_diverged, current_diverged)
        self.assertEquals(tm_other, other)
        self.assertEquals([], divergences)

    def test_get_all_important_translations_current_three_diverged_elsewhere(
        self):
        tm_diverged = make_translationmessage(
            self.factory, pofile=self.other_pofile, potmsgset=self.potmsgset,
            ubuntu=True, upstream=False, diverged=True)
        self.assertTrue(tm_diverged.is_current_ubuntu)
        self.assertEquals(
            tm_diverged.potemplate, self.other_pofile.potemplate)
        self.assertEquals(tm_diverged.potmsgset, self.potmsgset)
        current_shared, current_diverged, other, divergences = (
            get_all_important_translations(self.pofile, self.potmsgset))
        self.assertIs(None, current_shared)
        self.assertIs(None, current_diverged)
        self.assertIs(None, other)
        self.assertEquals([tm_diverged], divergences)
