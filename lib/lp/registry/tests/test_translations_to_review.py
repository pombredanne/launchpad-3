# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test the choice of "translations to review" for a user."""

__metaclass__ = type

from datetime import timedelta, datetime
from pytz import timezone
from unittest import TestLoader

from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.translator import TranslatorSet
from canonical.testing import DatabaseFunctionalLayer

from lp.testing import TestCaseWithFactory
from lp.services.worlddata.model.language import LanguageSet


UTC = timezone('UTC')


class ReviewTestMixin:
    """Base for testing which translations a reviewer can review."""
    def setUpMixin(self, for_product=True):
        """Set up test environment.

        Sets up a person, as well as a translation that that person is a
        reviewer for and has contributed to.

        If for_product is true, the translation will be for a product.
        Otherwise, it will be for a distribution.
        """
        # Set up a person, and a translation that this person is a
        # reviewer for and has contributed to.
        self.base_time = datetime.now(UTC)
        self.person = self.factory.makePerson()
        self.translationgroup = self.factory.makeTranslationGroup(
            owner=self.factory.makePerson())
        self.dutch = LanguageSet().getLanguageByCode('nl')
        TranslatorSet().new(
            translationgroup=self.translationgroup, language=self.dutch,
            translator=self.person)

        if for_product:
            self.distroseries = None
            self.distribution = None
            self.sourcepackagename = None
            self.productseries = removeSecurityProxy(
                self.factory.makeProductSeries())
            self.product = self.productseries.product
            self.supercontext = self.product
        else:
            self.productseries = None
            self.product = None
            self.distroseries = removeSecurityProxy(
                self.factory.makeDistroRelease())
            self.distribution = self.distroseries.distribution
            self.distribution.translation_focus = self.distroseries
            self.sourcepackagename = self.factory.makeSourcePackageName()
            self.supercontext = self.distribution

        self.supercontext.translationgroup = self.translationgroup
        self.supercontext.official_rosetta = True

        self.potemplate = self.factory.makePOTemplate(
            productseries=self.productseries, distroseries=self.distroseries,
            sourcepackagename=self.sourcepackagename)
        self.pofile = removeSecurityProxy(self.factory.makePOFile(
            potemplate=self.potemplate, language_code='nl'))
        self.potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.potemplate, singular='hi', sequence=1)
        self.translation = self.factory.makeTranslationMessage(
            potmsgset=self.potmsgset, pofile=self.pofile,
            translator=self.person, translations=['bi'],
            date_updated=self.base_time)

        later_time = self.base_time + timedelta(0, 0, 1)
        self.suggestion = removeSecurityProxy(
            self.factory.makeTranslationMessage(
                potmsgset=self.potmsgset, pofile=self.pofile,
                translator=self.factory.makePerson(), translations=['wi'],
                date_updated=later_time, suggestion=True))

        self.assertTrue(self.translation.is_current)
        self.pofile.updateStatistics()
        self.assertEqual(self.pofile.unreviewed_count, 1)


class ReviewableTranslationFilesTest:
    """Test getReviewableTranslationFiles for a given setup.

    Can be applied to product or distribution setups.
    """
    def _getReviewables(self, *args, **kwargs):
        """Shorthand for self.person.getReviewableTranslationFiles."""
        return list(self.person.getReviewableTranslationFiles(
            *args, **kwargs))

    def test_OneFileToReview(self):
        # In the base case, the method finds one POFile for self.person
        # to review.
        self.assertEqual(self._getReviewables(), [self.pofile])

    def test_getReviewableTranslationFiles_no_older_than_pass(self):
        # The no_older_than parameter keeps translations that the
        # reviewer worked on at least that recently.
        self.assertEqual(
            self._getReviewables(no_older_than=self.base_time), [self.pofile])

    def test_getReviewableTranslationFiles_no_older_than_filter(self):
        # The no_older_than parameter filters translations that the
        # reviewer has not worked on since the given time.
        next_day = self.base_time + timedelta(1, 0, 0)
        self.assertEqual(self._getReviewables(no_older_than=next_day), [])

    def test_NotTranslatingInLaunchpad(self):
        # We don't see products/distros that don't use Launchpad for
        # translations.
        self.supercontext.official_rosetta = False
        self.assertEqual(self._getReviewables(), [])

    def test_NonReviewer(self):
        # The method does not show translations that the user is not a
        # reviewer for.
        self.supercontext.translationgroup = None
        self.assertEqual(self._getReviewables(), [])

    def test_OtherLanguage(self):
        # We only get translations in languages that the person is a
        # reviewer for.
        self.pofile.language = LanguageSet().getLanguageByCode('de')
        self.assertEqual(self._getReviewables(), [])

    def test_NoNewSuggestions(self):
        # Translation files only show up if they have new suggestions.
        self.suggestion.date_created -= timedelta(2)
        self.pofile.updateStatistics()
        self.assertEqual(self._getReviewables(), [])


class TestReviewableProductTranslationFiles(TestCaseWithFactory,
                                            ReviewTestMixin,
                                            ReviewableTranslationFilesTest):
    """Test `Person.getReviewableTranslationFiles` for products."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestReviewableProductTranslationFiles, self).setUp()
        ReviewTestMixin.setUpMixin(self, for_product=True)


class TestReviewableDistroTranslationFiles(TestCaseWithFactory,
                                           ReviewTestMixin,
                                           ReviewableTranslationFilesTest):
    """Test `Person.getReviewableTranslationFiles` for distros."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestReviewableDistroTranslationFiles, self).setUp()
        ReviewTestMixin.setUpMixin(self, for_product=False)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
