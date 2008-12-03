# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of IQuestionTarget."""

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login_person
from canonical.launchpad.interfaces.distribution import IDistributionSet
from canonical.launchpad.interfaces.language import ILanguageSet
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class TestQuestionTarget_answer_contacts_with_languages(TestCaseWithFactory):
    """Tests for the 'answer_contacts_with_languages' property of question
    targets.
    """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestQuestionTarget_answer_contacts_with_languages, self).setUp()
        self.answer_contact = self.factory.makePerson()
        login_person(self.answer_contact)
        lang_set = getUtility(ILanguageSet)
        self.answer_contact.addLanguage(lang_set['pt_BR'])
        self.answer_contact.addLanguage(lang_set['en'])

    def test_Product_implementation_should_prefill_cache(self):
        # Remove the answer contact's security proxy because we need to call
        # some non public methods to change its language cache.
        answer_contact = removeSecurityProxy(self.answer_contact)
        product = self.factory.makeProduct()
        product.addAnswerContact(answer_contact)

        # Must delete the cache because it's been filled in addAnswerContact.
        answer_contact.deleteLanguagesCache()
        self.assertRaises(AttributeError, answer_contact.getLanguagesCache)

        # Need to remove the product's security proxy because
        # answer_contacts_with_languages is not part of its public API.
        answer_contacts = removeSecurityProxy(
            product).answer_contacts_with_languages
        self.failUnlessEqual(answer_contacts, [answer_contact])
        langs = [
            lang.englishname for lang in answer_contact.getLanguagesCache()]
        # The languages cache has been filled in the correct order.
        self.failUnlessEqual(langs, [u'English', u'Portuguese (Brazil)'])

    def test_SourcePackage_implementation_should_prefill_cache(self):
        # Remove the answer contact's security proxy because we need to call
        # some non public methods to change its language cache.
        answer_contact = removeSecurityProxy(self.answer_contact)
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        self.factory.makeSourcePackageName(name='test-pkg')
        source_package = ubuntu.getSourcePackage('test-pkg')
        source_package.addAnswerContact(answer_contact)

        # Must delete the cache because it's been filled in addAnswerContact.
        answer_contact.deleteLanguagesCache()
        self.assertRaises(AttributeError, answer_contact.getLanguagesCache)

        # Need to remove the sourcepackage's security proxy because
        # answer_contacts_with_languages is not part of its public API.
        answer_contacts = removeSecurityProxy(
            source_package).answer_contacts_with_languages
        self.failUnlessEqual(answer_contacts, [answer_contact])
        langs = [
            lang.englishname for lang in answer_contact.getLanguagesCache()]
        # The languages cache has been filled in the correct order.
        self.failUnlessEqual(langs, [u'English', u'Portuguese (Brazil)'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
