# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from unittest import TestLoader

from zope.security.proxy import removeSecurityProxy

from lp.testing import TestCaseWithFactory
from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from lp.services.worlddata.model.language import LanguageSet
from lp.translations.browser.person import PersonTranslationView
from lp.translations.model.productserieslanguage import ProductSeriesLanguage
from lp.translations.model.translator import TranslatorSet


class TestPersonTranslationView(TestCaseWithFactory):
    """Test `PersonTranslationView`."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestPersonTranslationView, self).setUp()
        person = removeSecurityProxy(self.factory.makePerson())
        self.view = PersonTranslationView(person, LaunchpadTestRequest())

    def _makeReviewer(self):
        """Set up the person we're looking at as a Dutch reviewer."""
        owner = self.factory.makePerson()
        self.translationgroup = self.factory.makeTranslationGroup(owner=owner)
        dutch = LanguageSet().getLanguageByCode('nl')
        TranslatorSet().new(
            translationgroup=self.translationgroup, language=dutch,
            translator=self.view.context)

    def _makePOFiles(self, count, previously_worked_on):
        """Create `count` `POFile`s that the view's person can review.

        :param count: Number of POFiles to create.
        :param previously_worked_on: Whether these should be POFiles
            that the person has already worked on.
        """
        pofiles = []
        for counter in xrange(count):
            pofile = self.factory.makePOFile(language_code='nl')
            product = pofile.potemplate.productseries.product
            product.translationgroup = self.translationgroup

            if previously_worked_on:
                potmsgset = self.factory.makePOTMsgSet(
                    potemplate=pofile.potemplate, singular='x', sequence=1)
                self.factory.makeTranslationMessage(
                    potmsgset=potmsgset, pofile=pofile,
                    translator=self.view.context, translations=['y'])

            removeSecurityProxy(pofile).unreviewed_count = 1
            pofiles.append(pofile)

        return pofiles

    def test_translation_groups(self):
        # translation_groups lists the translation groups a person is
        # in.
        self._makeReviewer()
        self.assertEqual(
            [self.translationgroup], self.view.translation_groups)

    def test_person_is_reviewer_false(self):
        # A regular person is not a reviewer.
        self.assertFalse(self.view.person_is_reviewer)

    def test_person_is_reviewer_true(self):
        # A person who's in a translation group is a reviewer.
        self._makeReviewer()
        self.assertTrue(self.view.person_is_reviewer)

    def test_findBestCommonReviewLinks_single_pofile(self):
        # If passed a single POFile, _findBestCommonReviewLinks returns
        # a list of just that POFile.
        pofile = self.factory.makePOFile(language_code='lua')
        links = self.view._findBestCommonReviewLinks([pofile])
        self.assertEqual(self.view._composeReviewLinks([pofile]), links)

    def test_findBestCommonReviewLinks_product_wild_mix(self):
        # A combination of wildly different POFiles in the same product
        # yields links to the individual POFiles.
        pofile1 = self.factory.makePOFile(language_code='sux')
        product = pofile1.potemplate.productseries.product
        series2 = self.factory.makeProductSeries(product)
        template2 = self.factory.makePOTemplate(productseries=series2)
        pofile2 = self.factory.makePOFile(
            potemplate=template2, language_code='la')

        links = self.view._findBestCommonReviewLinks([pofile1, pofile2])

        expected_links = self.view._composeReviewLinks([pofile1, pofile2])
        self.assertEqual(expected_links, links)

    def test_findBestCommonReviewLinks_different_templates(self):
        # A combination of POFiles in the same language but different
        # templates of the same productseries is represented as a link
        # to the ProductSeriesLanguage.
        pofile1 = self.factory.makePOFile(language_code='nl')
        series = pofile1.potemplate.productseries
        template2 = self.factory.makePOTemplate(productseries=series)
        pofile2 = self.factory.makePOFile(
            potemplate=template2, language_code='nl')

        links = self.view._findBestCommonReviewLinks([pofile1, pofile2])

        productserieslanguage = ProductSeriesLanguage(
            series, pofile1.language)
        self.assertEqual([canonical_url(productserieslanguage)], links)

    def test_findBestCommonReviewLinks_different_languages(self):
        # If the POFiles differ only in language, we get a link to the
        # overview for the template.
        pofile1 = self.factory.makePOFile(language_code='nl')
        template = pofile1.potemplate
        pofile2 = self.factory.makePOFile(
            potemplate=template, language_code='lo')

        links = self.view._findBestCommonReviewLinks([pofile1, pofile2])

        self.assertEqual([canonical_url(template)], links)

    def test_findBestCommonReviewLinks_sharing_pofiles(self):
        # In a Product, two POFiles may share their translations.  For
        # now, we link to each individually.  We may want to make this
        # more clever in the future.
        pofile1 = self.factory.makePOFile(language_code='nl')
        template1 = pofile1.potemplate
        series1 = template1.productseries
        series2 = self.factory.makeProductSeries(product=series1.product)
        template2 = self.factory.makePOTemplate(
            productseries=series2, name=template1.name,
            translation_domain=template1.translation_domain)
        pofile2 = template2.getPOFileByLang('nl')

        pofiles = [pofile1, pofile2]
        links = self.view._findBestCommonReviewLinks(pofiles)

        self.assertEqual(self.view._composeReviewLinks(pofiles), links)

    def test_findBestCommonReviewLinks_package_different_languages(self):
        # For package POFiles in the same template but different
        # languages, we link to the template.
        package = self.factory.makeSourcePackage()
        package.distroseries.distribution.official_rosetta = True
        template = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        pofile1 = self.factory.makePOFile(
            potemplate=template, language_code='nl')
        pofile2 = self.factory.makePOFile(
            potemplate=template, language_code='ka')

        links = self.view._findBestCommonReviewLinks([pofile1, pofile2])
        self.assertEqual([canonical_url(template)], links)

    def test_findBestCommonReviewLinks_package_different_templates(self):
        # For package POFiles in different templates, we to the
        # package's template list.  There is no "source package series
        # language" page.
        package = self.factory.makeSourcePackage()
        package.distroseries.distribution.official_rosetta = True
        template1 = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        template2 = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        pofile1 = self.factory.makePOFile(
            potemplate=template1, language_code='nl')
        pofile2 = self.factory.makePOFile(
            potemplate=template2, language_code='nl')

        links = self.view._findBestCommonReviewLinks([pofile1, pofile2])

        self.assertEqual([canonical_url(package)], links)

    def test_describeReviewableTarget_string_count(self):
        # _describeReviewableTarget puts out a human-readable
        # description of how many strings need review.
        product = self.factory.makeProduct()

        description = self.view._describeReviewableTarget(
            product, canonical_url(product), 0)
        self.assertEqual(description['count'], 0)
        self.assertEqual(description['count_wording'], '0 strings')

        # Singular applies for exactly 1 string.
        description = self.view._describeReviewableTarget(
            product, canonical_url(product), 1)
        self.assertEqual(description['count'], 1)
        self.assertEqual(description['count_wording'], '1 string')


        description = self.view._describeReviewableTarget(
            product, canonical_url(product), 2)
        self.assertEqual(description['count'], 2)
        self.assertEqual(description['count_wording'], '2 strings')

    def test_describeReviewableTarget_product(self):
        # _describeReviewableTarget describes a Product with reviewable
        # translations.
        product = self.factory.makeProduct()
        link = canonical_url(product)

        description = self.view._describeReviewableTarget(product, link, 99)

        expected_description = {
            'target': product,
            'count': 99,
            'count_wording': "99 strings",
            'is_product': True,
            'link': link,
        }
        self.assertEqual(expected_description, description)

    def test_describeReviewableTarget_package(self):
        # _describeReviewableTarget describes a package with reviewable
        # translations.
        package = self.factory.makeSourcePackage()
        package.distroseries.distribution.official_rosetta = True
        target = (package.sourcepackagename, package.distroseries)
        link = canonical_url(package)

        description = self.view._describeReviewableTarget(target, link, 42)

        expected_description = {
            'target': package,
            'count': 42,
            'count_wording': "42 strings",
            'is_product': False,
            'link': link,
        }
        self.assertEqual(expected_description, description)

    def test_aggregateTranslationTargets(self):
        # _aggregateTranslationTargets represents a series of POFiles as
        # a series of target descriptions, aggregating where possible.

        # Trivial case: no POFiles means no targets.
        self.assertEqual([], self.view._aggregateTranslationTargets([]))

        # Basic case: one POFile yields its product or package.
        pofile = self.factory.makePOFile(language_code='ca')

        description = self.view._aggregateTranslationTargets([pofile])

        expected_links = self.view._composeReviewLinks([pofile])
        expected_description = [{
            'target': pofile.potemplate.productseries.product,
            'count': 0,
            'count_wording': "0 strings",
            'is_product': True,
            'link': expected_links[0],
        }]
        self.assertEqual(expected_description, description)

    def test_aggregateTranslationTargets_product_and_package(self):
        # _aggregateTranslationTargets keeps a product and a package
        # separate.
        product_pofile = self.factory.makePOFile(language_code='th')
        removeSecurityProxy(product_pofile).unreviewed_count = 1

        package = self.factory.makeSourcePackage()
        package.distroseries.distribution.official_rosetta = True
        package_template = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        package_pofile = self.factory.makePOFile(
            potemplate=package_template, language_code='th')
        removeSecurityProxy(package_pofile).unreviewed_count = 2

        descriptions = self.view._aggregateTranslationTargets(
            [product_pofile, package_pofile])
        links = set(entry['link'] for entry in descriptions)

        expected_links = set(
            self.view._composeReviewLinks([product_pofile, package_pofile]))
        self.assertEqual(expected_links, links)

    def test_aggregateTranslationTargets_bundles_productseries(self):
        # _aggregateTranslationTargets describes POFiles for the same
        # ProductSeries together.
        pofile1 = self.factory.makePOFile(language_code='es')
        series = pofile1.potemplate.productseries
        template2 = self.factory.makePOTemplate(productseries=series)
        pofile2 = self.factory.makePOFile(
            language_code='br', potemplate=template2)
        
        description = self.view._aggregateTranslationTargets(
            [pofile1, pofile2])

        self.assertEqual(1, len(description))
        self.assertEqual(canonical_url(series), description[0]['link'])

    def test_aggregateTranslationTargets_bundles_package(self):
        # _aggregateTranslationTargets describes POFiles for the same
        # ProductSeries together.
        package = self.factory.makeSourcePackage()
        package.distroseries.distribution.official_rosetta = True
        template1 = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        pofile1 = self.factory.makePOFile(
            language_code='es', potemplate=template1)
        template2 = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        pofile2 = self.factory.makePOFile(
            language_code='br', potemplate=template2)
        
        description = self.view._aggregateTranslationTargets(
            [pofile1, pofile2])

        self.assertEqual(1, len(description))
        self.assertEqual(canonical_url(package), description[0]['link'])

    def test_num_projects_and_packages_to_review(self):
        # num_projects_and_packages_to_review counts the number of
        # reviewable targets that the person has worked on.
        self._makeReviewer()

        self._makePOFiles(1, previously_worked_on=True)

        self.assertEqual(1, self.view.num_projects_and_packages_to_review)

    def test_num_projects_and_packages_to_review_zero(self):
        # num_projects_and_packages does not count new suggestions.
        self._makeReviewer()

        self._makePOFiles(1, previously_worked_on=False)

        self.assertEqual(0, self.view.num_projects_and_packages_to_review)

    def test_top_projects_and_packages_to_review(self):
        # top_projects_and_packages_to_review tries to name at least one
        # translation target that the person has worked on, and at least
        # one random suggestion that the person hasn't worked on.
        self._makeReviewer()
        pofile_worked_on = self._makePOFiles(1, previously_worked_on=True)[0]
        pofile_not_worked_on = self._makePOFiles(
            1, previously_worked_on=False)[0]

        targets = self.view.top_projects_and_packages_to_review

        expected_links = self.view._composeReviewLinks(
            [pofile_worked_on, pofile_not_worked_on])
        self.assertEqual(
            set(expected_links), set(item['link'] for item in targets))

    def test_top_projects_and_packages_caps_existing_involvement(self):
        # top_projects_and_packages will return at most 9 POFiles that
        # the person has already worked on.
        self._makeReviewer()
        self._makePOFiles(10, previously_worked_on=True)

        targets = self.view.top_projects_and_packages_to_review

        self.assertEqual(9, len(targets))
        self.assertEqual(9, len(set(item['link'] for item in targets)))

    def test_top_projects_and_packages_caps_suggestions(self):
        # top_projects_and_packages will suggest at most 10 POFiles that
        # the person has not worked on.
        self._makeReviewer()
        self._makePOFiles(11, previously_worked_on=False)

        targets = self.view.top_projects_and_packages_to_review

        self.assertEqual(10, len(targets))
        self.assertEqual(10, len(set(item['link'] for item in targets)))

    def test_top_projects_and_packages_caps_total(self):
        # top_projects_and_packages will show at most 10 POFiles
        # overall.  The last one will be a suggestion.
        self._makeReviewer()
        pofiles_worked_on = self._makePOFiles(11, previously_worked_on=True)
        pofiles_not_worked_on = self._makePOFiles(
            11, previously_worked_on=False)

        targets = self.view.top_projects_and_packages_to_review

        self.assertEqual(10, len(targets))
        self.assertEqual(10, len(set(item['link'] for item in targets)))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
