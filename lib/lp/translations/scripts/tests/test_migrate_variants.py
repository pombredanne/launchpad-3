# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory
from lp.translations.scripts.migrate_variants import MigrateVariantsProcess


class TestMigrateVariants(TestCaseWithFactory):
    """Test variant migration."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # This test needs the privileges of rosettaadmin (to update
        # TranslationMessages) but it also needs to set up test conditions
        # which requires other privileges.
        self.layer.switchDbUser('postgres')
        super(TestMigrateVariants, self).setUp(user='mark@example.com')
        self.migrate_process = MigrateVariantsProcess(self.layer.txn)
        self.language_set = getUtility(ILanguageSet)

    def test_fetchAllLanguagesWithVariants(self):
        all_langs = self.migrate_process.fetchAllLanguagesWithVariants()
        self.assertContentEqual([], all_langs)

    def _sortLanguageVariantPairs(self, lang_vars):
        cmp_pairs = lambda a, b: cmp(a[0].code, b[0].code) or cmp(a[1], b[1])
        return sorted(lang_vars, cmp=cmp_pairs)

    def assertLanguageListsEqual(self, a, b):
        # We provide our own assertion because assertContentEqual does
        # only naive sorting and that doesn't always work with tuples
        # which might have an identical first element, but differ on
        # the second element.
        self.assertEqual(
            self._sortLanguageVariantPairs(a),
            self._sortLanguageVariantPairs(b))

    def test_fetchAllLanguagesWithVariants_pofiles(self):
        serbian_pofile = self.factory.makePOFile('sr', variant=u'test')
        serbian = serbian_pofile.language
        self.layer.txn.commit()
        all_langs = self.migrate_process.fetchAllLanguagesWithVariants()
        self.assertLanguageListsEqual(
            [(serbian, u'test')], all_langs)

    def test_fetchAllLanguagesWithVariants_pofile_and_translation(self):
        # With both a POFile and TranslationMessage for the same language
        # and variant, the pair is returned only once.
        serbian_pofile = self.factory.makePOFile('sr', variant=u'test')
        serbian = serbian_pofile.language
        message = self.factory.makeTranslationMessage(pofile=serbian_pofile)
        self.layer.txn.commit()

        all_langs = self.migrate_process.fetchAllLanguagesWithVariants()
        self.assertLanguageListsEqual(
            [(serbian, u'test')], all_langs)

    def test_fetchAllLanguagesWithVariants_translationmessages(self):
        # We create a TranslationMessage with no matching PO file
        # by first creating it attached to sr@test POFile, and then
        # directly changing the variant on it.
        serbian_pofile = self.factory.makePOFile('sr', variant=u'test')
        serbian = serbian_pofile.language
        message = self.factory.makeTranslationMessage(pofile=serbian_pofile)
        message.variant = u'another'
        self.layer.txn.commit()

        all_langs = self.migrate_process.fetchAllLanguagesWithVariants()
        self.assertLanguageListsEqual(
            [(serbian, u'test'), (serbian, u'another')],
            all_langs)

    def test_getOrCreateLanguage_new(self):
        serbian = self.language_set.getLanguageByCode('sr')
        new_language = self.migrate_process.getOrCreateLanguage(
            serbian, u'test')
        self.assertEqual(u'sr@test', new_language.code)
        self.assertEqual(u'Serbian test', new_language.englishname)
        self.assertEqual(serbian.pluralforms, new_language.pluralforms)
        self.assertEqual(serbian.pluralexpression,
                         new_language.pluralexpression)
        self.assertEqual(serbian.direction, new_language.direction)

    def test_getOrCreateLanguage_noop(self):
        serbian = self.language_set.getLanguageByCode('sr')
        serbian_test = self.language_set.createLanguage(
            'sr@test', 'Serbian test')
        new_language = self.migrate_process.getOrCreateLanguage(
            serbian, u'test')
        self.assertEqual(serbian_test, new_language)

    def test_getPOFileIDsForLanguage_none(self):
        serbian = self.language_set.getLanguageByCode('sr')
        pofile_ids = self.migrate_process.getPOFileIDsForLanguage(
            serbian, u'test')
        self.assertContentEqual([], list(pofile_ids))

    def test_getPOFileIDsForLanguage_variant(self):
        serbian = self.language_set.getLanguageByCode('sr')
        sr_pofile = self.factory.makePOFile(serbian.code, variant=u'test')
        pofile_ids = self.migrate_process.getPOFileIDsForLanguage(
            serbian, u'test')
        self.assertContentEqual([sr_pofile.id], list(pofile_ids))

    def test_getPOFileIDsForLanguage_nonvariant(self):
        serbian = self.language_set.getLanguageByCode('sr')
        sr_pofile = self.factory.makePOFile(serbian.code, variant=None)
        pofile_ids = self.migrate_process.getPOFileIDsForLanguage(
            serbian, u'test')
        self.assertContentEqual([], list(pofile_ids))

    def test_getTranslationMessageIDsForLanguage_none(self):
        serbian = self.language_set.getLanguageByCode('sr')
        tm_ids = self.migrate_process.getTranslationMessageIDsForLanguage(
            serbian, u'test')
        self.assertContentEqual([], list(tm_ids))

    def test_getTranslationMessageIDsForLanguage_variant(self):
        serbian = self.language_set.getLanguageByCode('sr')
        sr_pofile = self.factory.makePOFile(serbian.code, variant=u'test')
        message = self.factory.makeTranslationMessage(sr_pofile)
        message.variant = u'test'
        tm_ids = self.migrate_process.getTranslationMessageIDsForLanguage(
            serbian, u'test')
        self.assertContentEqual([message.id], list(tm_ids))

    def test_getTranslationMessageIDsForLanguage_nonvariant(self):
        serbian = self.language_set.getLanguageByCode('sr')
        sr_pofile = self.factory.makePOFile(serbian.code, variant=None)
        message = self.factory.makeTranslationMessage(sr_pofile)
        tm_ids = self.migrate_process.getTranslationMessageIDsForLanguage(
            serbian, u'test')
        self.assertContentEqual([], list(tm_ids))
