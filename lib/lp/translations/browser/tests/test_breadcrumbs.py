# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.layers import TranslationsLayer
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)

from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.translations.interfaces.distroserieslanguage import (
    IDistroSeriesLanguageSet)
from lp.translations.interfaces.productserieslanguage import (
    IProductSeriesLanguageSet)
from lp.translations.interfaces.translationgroup import ITranslationGroupSet


class BaseTranslationsBreadcrumbTestCase(BaseBreadcrumbTestCase):
    request_layer = TranslationsLayer

    def setUp(self):
        super(BaseTranslationsBreadcrumbTestCase, self).setUp()
        self.traversed_objects = [self.root]

    def _testContextBreadcrumbs(self, traversal_list, links, texts, url=None):
        self.traversed_objects.extend(traversal_list)
        if url is None:
            url = canonical_url(traversal_list[-1], rootsite='translations')

        self.assertEquals(
            links,
            self._getBreadcrumbsURLs(url, self.traversed_objects))
        self.assertEquals(
            texts,
            self._getBreadcrumbsTexts(url, self.traversed_objects))


class TestTranslationsVHostBreadcrumb(BaseTranslationsBreadcrumbTestCase):

    def test_product(self):
        product = self.factory.makeProduct(
            name='crumb-tester', displayname="Crumb Tester")
        self._testContextBreadcrumbs(
            [product],
            ['http://launchpad.dev/crumb-tester',
             'http://translations.launchpad.dev/crumb-tester'],
            ["Crumb Tester", "Translations"])

    def test_productseries(self):
        product = self.factory.makeProduct(
            name='crumb-tester', displayname="Crumb Tester")
        series = self.factory.makeProductSeries(name="test", product=product)
        self._testContextBreadcrumbs(
            [product, series],
            ['http://launchpad.dev/crumb-tester',
             'http://launchpad.dev/crumb-tester/test',
             'http://translations.launchpad.dev/crumb-tester/test'],
            ["Crumb Tester", "Series test", "Translations"])

    def test_distribution(self):
        distribution = self.factory.makeDistribution(
            name='crumb-tester', displayname="Crumb Tester")
        self._testContextBreadcrumbs(
            [distribution],
            ['http://launchpad.dev/crumb-tester',
             'http://translations.launchpad.dev/crumb-tester'],
            ["Crumb Tester", "Translations"])

    def test_distroseries(self):
        distribution = self.factory.makeDistribution(
            name='crumb-tester', displayname="Crumb Tester")
        series = self.factory.makeDistroRelease(
            name="test", version="1.0", distribution=distribution)
        self._testContextBreadcrumbs(
            [distribution, series],
            ['http://launchpad.dev/crumb-tester',
             'http://launchpad.dev/crumb-tester/test',
             'http://translations.launchpad.dev/crumb-tester/test'],
            ["Crumb Tester", "1.0", "Translations"])

    def test_project(self):
        project = self.factory.makeProject(
            name='crumb-tester', displayname="Crumb Tester")
        self._testContextBreadcrumbs(
            [project],
            ['http://launchpad.dev/crumb-tester',
             'http://translations.launchpad.dev/crumb-tester'],
            ["Crumb Tester", "Translations"])

    def test_person(self):
        person = self.factory.makePerson(
            name='crumb-tester', displayname="Crumb Tester")
        self._testContextBreadcrumbs(
            [person],
            ['http://launchpad.dev/~crumb-tester',
             'http://translations.launchpad.dev/~crumb-tester'],
            ["Crumb Tester", "Translations"])


class TestTranslationGroupsBreadcrumbs(BaseTranslationsBreadcrumbTestCase):

    def test_translationgroupset(self):
        group_set = getUtility(ITranslationGroupSet)
        url = canonical_url(group_set, rootsite='translations')
        self._testContextBreadcrumbs(
            [group_set],
            ['http://translations.launchpad.dev/+groups'],
            ['Translation groups'],
            url=url)

    def test_translationgroup(self):
        group_set = getUtility(ITranslationGroupSet)
        group = self.factory.makeTranslationGroup(
            name='test-translators', title='Test translators')
        self._testContextBreadcrumbs(
            [group_set, group],
            ["http://translations.launchpad.dev/+groups",
             "http://translations.launchpad.dev/+groups/test-translators"],
            ["Translation groups", "Test translators"])


class TestSeriesLanguageBreadcrumbs(BaseTranslationsBreadcrumbTestCase):
    def setUp(self):
        super(TestSeriesLanguageBreadcrumbs, self).setUp()
        self.language = getUtility(ILanguageSet)['sr']

    def test_distroserieslanguage(self):
        distribution = self.factory.makeDistribution(
            name='crumb-tester', displayname="Crumb Tester")
        series = self.factory.makeDistroRelease(
            name="test", version="1.0", distribution=distribution)
        serieslanguage = getUtility(IDistroSeriesLanguageSet).getDummy(
            series, self.language)
        self._testContextBreadcrumbs(
            [distribution, series, serieslanguage],
            ["http://launchpad.dev/crumb-tester",
             "http://launchpad.dev/crumb-tester/test",
             "http://translations.launchpad.dev/crumb-tester/test",
             "http://translations.launchpad.dev/crumb-tester/test/+lang/sr"],
            ["Crumb Tester", "1.0", "Translations", "Serbian (sr)"])

    def test_productserieslanguage(self):
        product = self.factory.makeProduct(
            name='crumb-tester', displayname="Crumb Tester")
        series = self.factory.makeProductSeries(
            name="test", product=product)
        serieslanguage = getUtility(IProductSeriesLanguageSet).getDummy(
            series, self.language)
        self._testContextBreadcrumbs(
            [product, series, serieslanguage],
            ["http://launchpad.dev/crumb-tester",
             "http://launchpad.dev/crumb-tester/test",
             "http://translations.launchpad.dev/crumb-tester/test",
             "http://translations.launchpad.dev/crumb-tester/test/+lang/sr"],
            ["Crumb Tester", "Series test", "Translations", "Serbian (sr)"])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
