# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Launchpad object factory."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.enums import CodeImportReviewStatus
from lp.testing import TestCaseWithFactory
from lp.services.worlddata.interfaces.language import ILanguage
from lp.testing.factory import is_security_proxied_or_harmless


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

    def test_is_security_proxied_or_harmless__none(self):
        # is_security_proxied_or_harmless() considers the None object
        # to be a harmless object.
        self.assertTrue(is_security_proxied_or_harmless(None))

    def test_is_security_proxied_or_harmless__int(self):
        # is_security_proxied_or_harmless() considers integers
        # to be harmless.
        self.assertTrue(is_security_proxied_or_harmless(1))

    def test_is_security_proxied_or_harmless__string(self):
        # is_security_proxied_or_harmless() considers strings
        # to be harmless.
        self.assertTrue(is_security_proxied_or_harmless('abc'))

    def test_is_security_proxied_or_harmless__unicode(self):
        # is_security_proxied_or_harmless() considers unicode objects
        # to be harmless.
        self.assertTrue(is_security_proxied_or_harmless(u'abc'))

    def test_is_security_proxied_or_harmless__proxied_object(self):
        # is_security_proxied_or_harmless() treats security proxied
        # objects as harmless.
        proxied_person = self.factory.makePerson()
        self.assertTrue(is_security_proxied_or_harmless(proxied_person))

    def test_is_security_proxied_or_harmless__unproxied_object(self):
        # is_security_proxied_or_harmless() treats security proxied
        # objects as harmless.
        unproxied_person = removeSecurityProxy(self.factory.makePerson())
        self.assertFalse(is_security_proxied_or_harmless(unproxied_person))

    def test_is_security_proxied_or_harmless__sequence_harmless_content(self):
        # is_security_proxied_or_harmless() checks all elements
        # of a sequence. If all elements are harmless, so is the
        # sequence.
        proxied_person = self.factory.makePerson()
        self.assertTrue(
            is_security_proxied_or_harmless([1, '2', proxied_person]))

    def test_is_security_proxied_or_harmless__sequence_harmful_content(self):
        # is_security_proxied_or_harmless() checks all elements
        # of a sequence. If at least one element is harmful, so is the
        # sequence.
        unproxied_person = removeSecurityProxy(self.factory.makePerson())
        self.assertFalse(
            is_security_proxied_or_harmless([1, '2', unproxied_person]))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
