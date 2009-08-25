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

    def test_num_projects_and_packages_to_review(self):
        # num_projects_and_packages_to_review counts the number of
        # reviewable targets that the person has worked on.
        self._makeReviewer()

        self._makePOFiles(1, previously_worked_on=True)

        self.assertEqual(1, self.view.num_projects_and_packages_to_review)

    def test_all_projects_and_packages_to_review_one(self):
        # all_projects_and_packages describes the translations available
        # for review by its person.
        self._makeReviewer()
        pofile = self._makePOFiles(1, previously_worked_on=True)[0]
        product = pofile.potemplate.productseries.product

        descriptions = self.view.all_projects_and_packages_to_review

        self.assertEqual(1, len(descriptions))
        self.assertEqual(product, descriptions[0]['target'])

    def test_all_projects_and_packages_to_review_none(self):
        # all_projects_and_packages_to_review works even if there is
        # nothing to review.  It will find nothing.
        self._makeReviewer()

        descriptions = self.view.all_projects_and_packages_to_review

        self.assertEqual([], descriptions)

    def test_all_projects_and_packages_to_review_string_singular(self):
        # A translation description says how many strings need review,
        # both as a number and as text.
        self._makeReviewer()
        pofile = self._makePOFiles(1, previously_worked_on=True)[0]
        removeSecurityProxy(pofile).unreviewed_count = 1

        description = self.view.all_projects_and_packages_to_review[0]

        self.assertEqual(1, description['count'])
        self.assertEqual("1 string", description['count_wording'])

    def test_all_projects_and_packages_to_review_string_plural(self):
        # For multiple strings, count_wording uses the plural.
        self._makeReviewer()
        pofile = self._makePOFiles(1, previously_worked_on=True)[0]
        removeSecurityProxy(pofile).unreviewed_count = 2

        description = self.view.all_projects_and_packages_to_review[0]

        self.assertEqual(2, description['count'])
        self.assertEqual("2 strings", description['count_wording'])

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

        pofile_suffix = '/+translate?show=new_suggestions'
        expected_links = [
            canonical_url(pofile_worked_on) + pofile_suffix,
            canonical_url(pofile_not_worked_on) + pofile_suffix,
            ]
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
