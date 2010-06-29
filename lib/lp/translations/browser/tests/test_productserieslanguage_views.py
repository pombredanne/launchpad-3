# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from lp.translations.browser.serieslanguage import (
    ProductSeriesLanguageView)
from lp.translations.interfaces.translator import ITranslatorSet
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from lp.translations.browser.productseries import ProductSeriesView
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory, login_person


class TestProductSeries(TestCaseWithFactory):
    """Test ProductSeries view in translations facet."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Create a productseries that uses translations.
        TestCaseWithFactory.setUp(self)
        self.productseries = self.factory.makeProductSeries()
        self.productseries.product.official_rosetta = True
        self.view = ProductSeriesView(self.productseries,
                                      LaunchpadTestRequest())

    def test_single_potemplate(self):
        # Make sure that `single_potemplate` is True only when
        # there is exactly one POTemplate for the ProductSeries.

        self.assertFalse(self.view.single_potemplate)

        potemplate1 = self.factory.makePOTemplate(
            productseries=self.productseries)

        # self.view may cache the old single_potemplate value, so create
        # a fresh view now that the underlying data has changed.
        fresh_view = ProductSeriesView(
            self.productseries, LaunchpadTestRequest())
        self.assertTrue(fresh_view.single_potemplate)

        potemplate2 = self.factory.makePOTemplate(
            productseries=self.productseries)
        fresh_view = ProductSeriesView(
            self.productseries, LaunchpadTestRequest())
        self.assertFalse(fresh_view.single_potemplate)

    def test_has_translation_documentation(self):
        self.assertFalse(self.view.has_translation_documentation)

        # Adding a translation group with no documentation keeps
        # `has_translation_documentation` at False.
        group = self.factory.makeTranslationGroup(
            self.productseries.product.owner, url=None)
        self.productseries.product.translationgroup = group
        self.assertFalse(self.view.has_translation_documentation)

        # When there is documentation URL, `has_translation_documentation`
        # is True.
        group.translation_guide_url = u'http://something'
        self.assertTrue(self.view.has_translation_documentation)

    def test_productserieslanguages(self):
        # With no POTemplates, it returns None.
        self.assertEquals(self.view.productserieslanguages,
                          None)

        # Adding a single POTemplate, but no actual translations
        # makes `productserieslanguages` return an empty list instead.
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        self.assertEquals(self.view.productserieslanguages,
                          [])

        # Adding a translation, adds that language to the list.
        pofile = self.factory.makePOFile('sr', potemplate)
        self.assertEquals(len(self.view.productserieslanguages),
                          1)
        self.assertEquals(self.view.productserieslanguages[0].language,
                          pofile.language)

        # If a user with another preferred languages looks at
        # the list, that language is combined with existing one.
        user = self.factory.makePerson()
        spanish = getUtility(ILanguageSet).getLanguageByCode('es')
        user.addLanguage(spanish)
        self.assertEquals(len(user.languages), 1)

        login_person(user)
        view = ProductSeriesView(self.productseries, LaunchpadTestRequest())
        # Returned languages are ordered by their name in English.
        self.assertEquals(
            [psl.language.englishname for psl in view.productserieslanguages],
            [u'Serbian', u'Spanish'])


    def test_productserieslanguages_english(self):
        # Even if there's an English POFile, it's not listed
        # among translated languages.
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        pofile = self.factory.makePOFile('en', potemplate)
        self.assertEquals(self.view.productserieslanguages,
                          [])

        # It's not shown even with more than one POTemplate
        # (different code paths).
        potemplate2 = self.factory.makePOTemplate(
            productseries=self.productseries)
        self.assertEquals(self.view.productserieslanguages,
                          [])


class TestProductSeriesLanguage(TestCaseWithFactory):
    """Test ProductSeriesLanguage view."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Create a productseries that uses translations.
        TestCaseWithFactory.setUp(self)
        self.productseries = self.factory.makeProductSeries()
        self.productseries.product.official_rosetta = True
        self.language = getUtility(ILanguageSet).getLanguageByCode('sr')
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        pofile = self.factory.makePOFile('sr', potemplate)
        self.psl = self.productseries.productserieslanguages[0]
        self.view = ProductSeriesLanguageView(
            self.psl, LaunchpadTestRequest())

    def test_empty_view(self):
        self.assertEquals(self.view.translation_group, None)
        self.assertEquals(self.view.translation_team, None)
        self.assertEquals(self.view.context, self.psl)

    def test_translation_group(self):
        group = self.factory.makeTranslationGroup(
            self.productseries.product.owner, url=None)
        self.productseries.product.translationgroup = group
        self.view.initialize()
        self.assertEquals(self.view.translation_group, group)

    def test_translation_team(self):
        # Just having a group doesn't mean there's a translation
        # team as well.
        group = self.factory.makeTranslationGroup(
            self.productseries.product.owner, url=None)
        self.productseries.product.translationgroup = group
        self.assertEquals(self.view.translation_team, None)

        # Setting a translator for this languages makes it
        # appear as the translation_team.
        team = self.factory.makeTeam()
        translator = getUtility(ITranslatorSet).new(
            group, self.language, team)
        # Recreate the view because we are using a cached property.
        self.view = ProductSeriesLanguageView(
            self.psl, LaunchpadTestRequest())
        self.view.initialize()
        self.assertEquals(self.view.translation_team, translator)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
