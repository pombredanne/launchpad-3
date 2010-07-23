# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Launchpad object factory."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.enums import CodeImportReviewStatus
from lp.testing import TestCaseWithFactory
from lp.services.worlddata.interfaces.language import ILanguage


class TestFactory(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_makeCodeImportNoStatus(self):
        # If makeCodeImport is not given a review status, it defaults to NEW.
        code_import = self.factory.makeCodeImport()
        self.assertEqual(
            CodeImportReviewStatus.NEW, code_import.review_status)

    def test_makeCodeImportReviewStatus(self):
        # If makeCodeImport is given a review status, then that is the status
        # of the created import.
        status = CodeImportReviewStatus.REVIEWED
        code_import = self.factory.makeCodeImport(review_status=status)
        self.assertEqual(status, code_import.review_status)

    def test_makeLanguage(self):
        # Without parameters, makeLanguage creates a language with code
        # starting with 'lang'.
        language = self.factory.makeLanguage()
        self.assertTrue(ILanguage.providedBy(language))
        self.assertTrue(language.code.startswith('lang'))
        # And name is constructed from code as 'Language %(code)s'.
        self.assertEquals('Language %s' % language.code,
                          language.englishname)

    def test_makeLanguage_with_code(self):
        # With language code passed in, that's used for the language.
        language = self.factory.makeLanguage('sr@test')
        self.assertEquals('sr@test', language.code)
        # And name is constructed from code as 'Language %(code)s'.
        self.assertEquals('Language sr@test', language.englishname)

    def test_makeLanguage_with_name(self):
        # Language name can be passed in to makeLanguage (useful for
        # use in page tests).
        language = self.factory.makeLanguage(name='Test language')
        self.assertTrue(ILanguage.providedBy(language))
        self.assertTrue(language.code.startswith('lang'))
        # And name is constructed from code as 'Language %(code)s'.
        self.assertEquals('Test language', language.englishname)

    def test_loginAsAnyone(self):
        # Login as anyone logs you in as any user.
        person = self.factory.loginAsAnyone()
        current_person = getUtility(ILaunchBag).user
        self.assertIsNot(None, person)
        self.assertEqual(person, current_person)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
