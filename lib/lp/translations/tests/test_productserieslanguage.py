# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.interface.verify import verifyObject
from zope.security.proxy import removeSecurityProxy

from lp.translations.interfaces.productserieslanguage import (
    IProductSeriesLanguage, IProductSeriesLanguageSet)
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory
from canonical.testing import ZopelessDatabaseLayer


class TestProductSeriesLanguages(TestCaseWithFactory):
    """Test ProductSeries.productserieslanguages implementation."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Create a productseries that uses translations.
        TestCaseWithFactory.setUp(self)
        self.productseries = self.factory.makeProductSeries()
        self.productseries.product.official_rosetta = True

    def test_NoTemplatesNoTranslation(self):
        # There are no templates and no translations.
        self.assertEquals(self.productseries.productserieslanguages,
                          [])

    def test_OneTemplateNoTranslation(self):
        # There is a template and no translations.
        self.factory.makePOTemplate(productseries=self.productseries)
        self.assertEquals(self.productseries.productserieslanguages,
                          [])

    def test_OneTemplateWithTranslations(self):
        # There is a template and one translation.
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)

        # Add a Serbian translation.
        serbian = getUtility(ILanguageSet).getLanguageByCode('sr')
        sr_pofile = self.factory.makePOFile(serbian.code, potemplate)

        psls = list(self.productseries.productserieslanguages)
        self.assertEquals(len(psls), 1)

        # ProductSeriesLanguage object correctly keeps values
        # for a language, productseries itself and POFile.
        sr_psl = psls[0]
        self.assertEquals(sr_psl.productseries, self.productseries)
        self.assertEquals(sr_psl.language, serbian)
        self.assertEquals(sr_psl.pofile, sr_pofile)

        # Add another translation (eg. "Albanian", so it sorts
        # it before Serbian).
        albanian = getUtility(ILanguageSet).getLanguageByCode('sq')
        sq_pofile = self.factory.makePOFile(albanian.code, potemplate)
        psls = list(self.productseries.productserieslanguages)
        self.assertEquals(len(psls), 2)

        # Ordering is alphabetic by English name of the language.
        self.assertEquals(psls[0].language, albanian)
        self.assertEquals(psls[1].language, serbian)

    def test_TwoTemplatesWithTranslations(self):
        # There is a template and one translation.
        potemplate1 = self.factory.makePOTemplate(
            productseries=self.productseries)
        potemplate2 = self.factory.makePOTemplate(
            productseries=self.productseries)
        potemplate1.priority = 1
        potemplate2.priority = 2

        # Add Serbian translation for one POTemplate.
        serbian = getUtility(ILanguageSet).getLanguageByCode('sr')
        pofile1 = self.factory.makePOFile(serbian.code, potemplate1)
        psls = list(self.productseries.productserieslanguages)
        self.assertEquals(len(psls), 1)

        # `pofile` is not set when there's more than one template.
        sr_psl = self.productseries.productserieslanguages[0]
        self.assertEquals(sr_psl.productseries, self.productseries)
        self.assertEquals(sr_psl.language, serbian)
        self.assertEquals(sr_psl.pofile, None)

        # Only this POFile is returned by the `pofiles` property.
        self.assertEquals(list(sr_psl.pofiles), [pofile1])

        # If we provide a POFile for the other template, `pofiles`
        # returns both (ordered by decreasing priority).
        pofile2 = self.factory.makePOFile(serbian.code, potemplate2)
        sr_psl = self.productseries.productserieslanguages[0]
        self.assertEquals(list(sr_psl.pofiles), [pofile2, pofile1])


class TestProductSeriesLanguageStatsCalculation(TestCaseWithFactory):
    """Test ProductSeriesLanguage statistics calculation."""

    layer = ZopelessDatabaseLayer

    def createPOTemplateWithPOTMsgSets(self, number_of_potmsgsets):
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        for sequence in range(number_of_potmsgsets):
            self.factory.makePOTMsgSet(potemplate, sequence=sequence+1)
        removeSecurityProxy(potemplate).messagecount = number_of_potmsgsets
        return potemplate

    def setPOFileStatistics(self, pofile, imported, changed, new, unreviewed,
                            date_changed):
        # Instead of creating all relevant translation messages, we
        # just fake cached statistics instead.
        naked_pofile = removeSecurityProxy(pofile)
        naked_pofile.currentcount = imported
        naked_pofile.updatescount = changed
        naked_pofile.rosettacount = new
        naked_pofile.unreviewed_count = unreviewed
        naked_pofile.date_changed = date_changed
        naked_pofile.sync()

    def setUp(self):
        # Create a productseries that uses translations.
        TestCaseWithFactory.setUp(self)
        self.productseries = self.factory.makeProductSeries()
        self.productseries.product.official_rosetta = True
        self.psl_set = getUtility(IProductSeriesLanguageSet)
        self.language = getUtility(ILanguageSet).getLanguageByCode('sr')

    def assertPSLStatistics(self, psl, stats):
        self.assertEquals(
            (psl.messageCount(),
             psl.translatedCount(),
             psl.currentCount(),
             psl.rosettaCount(),
             psl.updatesCount(),
             psl.unreviewedCount(),
             psl.last_changed_date),
             stats)

    def test_dummy_ProductSeriesLanguage(self):
        # With no templates all counts are zero.
        psl = self.psl_set.getProductSeriesLanguage(
            self.productseries, self.language)
        self.failUnless(verifyObject(IProductSeriesLanguage, psl))
        self.assertPSLStatistics(psl, (0, 0, 0, 0, 0, 0, None))

        # Adding a single template with 10 messages makes the total
        # count of messages go up to 10.
        potemplate = self.createPOTemplateWithPOTMsgSets(10)
        psl = self.psl_set.getProductSeriesLanguage(
            self.productseries, self.language)
        psl.recalculateCounts()
        self.assertPSLStatistics(
            psl, (10, 0, 0, 0, 0, 0, None))

    def test_OneTemplate(self):
        # With only one template, statistics match those of the POFile.
        potemplate = self.createPOTemplateWithPOTMsgSets(10)
        pofile = self.factory.makePOFile(self.language.code, potemplate)

        # Set statistics to 4 imported, 3 new in rosetta (out of which 2
        # are updates) and 5 with unreviewed suggestions.
        self.setPOFileStatistics(pofile, 4, 2, 3, 5, pofile.date_changed)

        # Getting PSL through PSLSet gives an uninitialized object.
        psl = self.psl_set.getProductSeriesLanguage(
            self.productseries, self.language)
        self.assertEquals(psl.messageCount(), 0)

        # We explicitely ask for stats to be recalculated.
        psl.recalculateCounts()

        self.assertPSLStatistics(psl,
                                 (pofile.messageCount(),
                                  pofile.translatedCount(),
                                  pofile.currentCount(),
                                  pofile.rosettaCount(),
                                  pofile.updatesCount(),
                                  pofile.unreviewedCount(),
                                  pofile.date_changed))

    def test_TwoTemplates(self):
        # With two templates, statistics are added up.
        potemplate1 = self.createPOTemplateWithPOTMsgSets(10)
        pofile1 = self.factory.makePOFile(self.language.code, potemplate1)
        # Set statistics to 4 imported, 3 new in rosetta (out of which 2
        # are updates) and 5 with unreviewed suggestions.
        self.setPOFileStatistics(pofile1, 4, 2, 3, 5, pofile1.date_changed)

        potemplate2 = self.createPOTemplateWithPOTMsgSets(20)
        pofile2 = self.factory.makePOFile(self.language.code, potemplate2)
        # Set statistics to 1 imported, 1 new in rosetta (which is also the
        # 1 update) and 1 with unreviewed suggestions.
        self.setPOFileStatistics(pofile2, 1, 1, 1, 1, pofile2.date_changed)

        psl = self.productseries.productserieslanguages[0]
        # We explicitely ask for stats to be recalculated.
        psl.recalculateCounts()

        # Total is a sum of totals in both POTemplates (10+20).
        # Translated is a sum of imported and rosetta translations,
        # which adds up as (4+3)+(1+1).
        self.assertPSLStatistics(psl, (30, 9, 5, 4, 3, 6,
            pofile2.date_changed))
        self.assertPSLStatistics(psl, (
            pofile1.messageCount() + pofile2.messageCount(),
            pofile1.translatedCount() + pofile2.translatedCount(),
            pofile1.currentCount() + pofile2.currentCount(),
            pofile1.rosettaCount() + pofile2.rosettaCount(),
            pofile1.updatesCount() + pofile2.updatesCount(),
            pofile1.unreviewedCount() + pofile2.unreviewedCount(),
            pofile2.date_changed))

    def test_recalculateCounts(self):
        # Test that recalculateCounts works correctly.
        potemplate1 = self.createPOTemplateWithPOTMsgSets(10)
        pofile1 = self.factory.makePOFile(self.language.code, potemplate1)

        # Set statistics to 1 imported, 3 new in rosetta (out of which 2
        # are updates) and 4 with unreviewed suggestions.
        self.setPOFileStatistics(pofile1, 1, 2, 3, 4, pofile1.date_changed)

        potemplate2 = self.createPOTemplateWithPOTMsgSets(20)
        pofile2 = self.factory.makePOFile(self.language.code, potemplate2)
        # Set statistics to 1 imported, 1 new in rosetta (which is also the
        # 1 update) and 1 with unreviewed suggestions.
        self.setPOFileStatistics(pofile2, 1, 1, 1, 1, pofile2.date_changed)

        psl = self.psl_set.getProductSeriesLanguage(self.productseries,
                                                    self.language)

        psl.recalculateCounts()
        # Total is a sum of totals in both POTemplates (10+20).
        # Translated is a sum of imported and rosetta translations,
        # which adds up as (1+3)+(1+1).
        # recalculateCounts() recalculates even the last changed date.
        self.assertPSLStatistics(psl, (30, 6, 2, 4, 3, 5,
            pofile2.date_changed))

    def test_recalculateCounts_no_pofiles(self):
        # Test that recalculateCounts works correctly even when there
        # are no POFiles returned.
        potemplate1 = self.createPOTemplateWithPOTMsgSets(1)
        potemplate2 = self.createPOTemplateWithPOTMsgSets(2)
        psl = self.psl_set.getProductSeriesLanguage(self.productseries,
                                                    self.language)
        psl.recalculateCounts()
        # And all the counts are zero.
        self.assertPSLStatistics(psl, (3, 0, 0, 0, 0, 0,
            None))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
