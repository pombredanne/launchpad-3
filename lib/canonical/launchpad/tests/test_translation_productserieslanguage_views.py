# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from lp.registry.browser.productseries import ProductSeriesView
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import TestCaseWithFactory, login_person
from canonical.testing import LaunchpadZopelessLayer


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
        self.assertTrue(self.view.single_potemplate)

        potemplate2 = self.factory.makePOTemplate(
            productseries=self.productseries)
        self.assertFalse(self.view.single_potemplate)

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
        self.assertEquals(
            [psl.language.code for psl in view.productserieslanguages],
            [u'sr', u'es'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
