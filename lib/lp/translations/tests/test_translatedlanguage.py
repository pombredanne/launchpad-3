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

    def getTranslatedLanguage(self, language):
        return self.psl_set.getProductSeriesLanguage(self.productseries,
                                                     language)

    def test_interface(self):
        language = self.factory.makeLanguage('sr@test')
        dummy_translated_language = self.getTranslatedLanguage(language)
        self.assertTrue(verifyObject(ITranslatedLanguage,
                                     dummy_translated_language))

    def test_language(self):
        language = self.factory.makeLanguage('sr@test')
        dummy_translated_language = self.getTranslatedLanguage(language)
        self.assertEqual(language,
                         dummy_translated_language.language)

    def test_parent(self):
        language = self.factory.makeLanguage('sr@test')
        dummy_translated_language = self.getTranslatedLanguage(language)
        self.assertEqual(self.parent,
                         dummy_translated_language.parent)
