# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.translations.browser.productseries import ProductSeriesView
from lp.translations.browser.serieslanguage import ProductSeriesLanguageView
from lp.translations.interfaces.translator import ITranslatorSet


class TestProductSeriesView(TestCaseWithFactory):
    """Test ProductSeries view in translations facet."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Create a productseries that uses translations.
        TestCaseWithFactory.setUp(self)
        self.productseries = self.factory.makeProductSeries()
        self.productseries.product.official_rosetta = True
        self.product = self.productseries.product

    def _createView(self):
        return ProductSeriesView(self.productseries, LaunchpadTestRequest())

    def test_single_potemplate_no_template(self):
        view = self._createView()
        self.assertFalse(view.single_potemplate)

    def test_single_potemplate_one_template(self):
        self.factory.makePOTemplate(productseries=self.productseries)
        view = self._createView()
        self.assertTrue(view.single_potemplate)

    def test_single_potemplate_multiple_templates(self):
        self.factory.makePOTemplate(productseries=self.productseries)
        self.factory.makePOTemplate(productseries=self.productseries)
        view = self._createView()
        self.assertFalse(view.single_potemplate)

    def test_has_translation_documentation_no_group(self):
        # Without a translation group, there is no documentation either.
        view = self._createView()
        self.assertFalse(view.has_translation_documentation)

    def test_has_translation_documentation_group_without_url(self):
        # Adding a translation group with no documentation keeps
        # `has_translation_documentation` at False.
        self.product.translationgroup = self.factory.makeTranslationGroup(
            self.productseries.product.owner, url=None)
        view = self._createView()
        self.assertFalse(view.has_translation_documentation)

    def test_has_translation_documentation_group_with_url(self):
        # After adding a translation group with a documentation URL lets
        # `has_translation_documentation` be True.
        self.product.translationgroup = self.factory.makeTranslationGroup(
            self.productseries.product.owner, url=u'http://something')
        view = self._createView()
        self.assertTrue(view.has_translation_documentation)

    def test_productserieslanguages_no_template(self):
        # With no POTemplates, no languages can be seen, either.
        view = self._createView()
        self.assertEquals(None, view.productserieslanguages)

    def _getProductserieslanguages(self, view):
        return [psl.language for psl in view.productserieslanguages]

    def test_productserieslanguages_without_pofile(self):
        # With a single POTemplate, but no actual translations, the list
        # of languages is empty.
        self.factory.makePOTemplate(productseries=self.productseries)
        view = self._createView()
        self.assertEquals([], self._getProductserieslanguages(view))

    def test_productserieslanguages_with_pofile(self):
        # The `productserieslanguages` properperty has a list of the
        # languages of the po files for the templates in this seris.
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        pofile = self.factory.makePOFile(potemplate=potemplate)
        view = self._createView()
        self.assertEquals(
            [pofile.language], self._getProductserieslanguages(view))

    def _makePersonWithLanguage(self):
        user = self.factory.makePerson()
        language = self.factory.makeLanguage()
        user.addLanguage(language)
        return user, language

    def test_productserieslanguages_preferred_language_without_pofile(self):
        # If the user has a preferred language, that language always in
        # the list.
        self.factory.makePOTemplate(
            productseries=self.productseries)
        user, language = self._makePersonWithLanguage()
        login_person(user)
        view = self._createView()
        self.assertEquals([language], self._getProductserieslanguages(view))

    def test_productserieslanguages_preferred_language_with_pofile(self):
        # If the user has a preferred language, that language always in
        # the list.
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        pofile = self.factory.makePOFile(potemplate=potemplate)
        user, language = self._makePersonWithLanguage()
        login_person(user)
        view = self._createView()
        self.assertContentEqual(
            [pofile.language, language],
            self._getProductserieslanguages(view))

    def test_productserieslanguages_ordered_by_englishname(self):
        # Returned languages are ordered by their name in English.
        language1 = self.factory.makeLanguage(
            language_code='lang-aa', name='Zz')
        language2 = self.factory.makeLanguage(
            language_code='lang-zz', name='Aa')
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        self.factory.makePOFile(language1.code, potemplate)
        self.factory.makePOFile(language2.code, potemplate)
        view = self._createView()
        self.assertEquals(
            [language2, language1], self._getProductserieslanguages(view))

    def test_productserieslanguages_english(self):
        # English is not listed among translated languages, even if there's
        # an English POFile
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        self.factory.makePOFile('en', potemplate)
        view = self._createView()
        self.assertEquals([], self._getProductserieslanguages(view))

        # It's not shown even with more than one POTemplate
        # (different code paths).
        self.factory.makePOTemplate(productseries=self.productseries)
        self.assertEquals([], self._getProductserieslanguages(view))


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
