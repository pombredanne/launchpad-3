# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.interface.verify import verifyObject
from zope.security.proxy import removeSecurityProxy

from lp.translations.interfaces.productserieslanguage import (
    IProductSeriesLanguageSet)
from lp.translations.interfaces.translations import ITranslatedLanguage
from lp.testing import TestCaseWithFactory
from canonical.testing import ZopelessDatabaseLayer


class TestTranslatedLanguageMixin(TestCaseWithFactory):
    """Test TranslatedLanguageMixin."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Create a productseries that uses translations.
        TestCaseWithFactory.setUp(self)
        self.productseries = self.factory.makeProductSeries()
        self.productseries.product.official_rosetta = True
        self.parent = self.productseries
        self.psl_set = getUtility(IProductSeriesLanguageSet)
        self.language = self.factory.makeLanguage('sr@test')

    def getTranslatedLanguage(self, language):
        return self.psl_set.getProductSeriesLanguage(self.productseries,
                                                     language)

    def addPOTemplate(self, number_of_potmsgsets=5):
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        for sequence in range(number_of_potmsgsets):
            self.factory.makePOTMsgSet(potemplate, sequence=sequence+1)
        removeSecurityProxy(potemplate).messagecount = number_of_potmsgsets
        return potemplate

    def test_interface(self):
        translated_language = self.getTranslatedLanguage(self.language)
        self.assertTrue(verifyObject(ITranslatedLanguage,
                                     translated_language))

    def test_language(self):
        translated_language = self.getTranslatedLanguage(self.language)
        self.assertEqual(self.language,
                         translated_language.language)

    def test_parent(self):
        translated_language = self.getTranslatedLanguage(self.language)
        self.assertEqual(self.parent,
                         translated_language.parent)

    def test_pofiles_notemplates(self):
        translated_language = self.getTranslatedLanguage(self.language)
        self.assertEqual([], list(translated_language.pofiles))

    def test_pofiles_template_with_pofiles(self):
        translated_language = self.getTranslatedLanguage(self.language)
        potemplate = self.addPOTemplate()
        pofile = self.factory.makePOFile(self.language.code, potemplate)
        self.assertEqual([pofile], list(translated_language.pofiles))

    def test_statistics_empty(self):
        translated_language = self.getTranslatedLanguage(self.language)

        expected = {
            'total_count' : 0,
            'translated_count' : 0,
            'new_count' : 0,
            'changed_count' : 0,
            'unreviewed_count' : 0,
            'untranslated_count' : 0,
            }
        self.assertEqual(expected,
                         translated_language.translation_statistics)

    def test_setCounts_statistics(self):
        translated_language = self.getTranslatedLanguage(self.language)

        total = 5
        translated = 4
        new = 3
        changed = 2
        unreviewed = 1
        untranslated = total - translated

        translated_language.setCounts(
            total, translated, new, changed, unreviewed)

        expected = {
            'total_count' : total,
            'translated_count' : translated,
            'new_count' : new,
            'changed_count' : changed,
            'unreviewed_count' : unreviewed,
            'untranslated_count' : untranslated,
            }
        self.assertEqual(expected,
                         translated_language.translation_statistics)
