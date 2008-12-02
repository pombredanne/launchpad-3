# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for methods of IQuestionTarget."""

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login_person
from canonical.launchpad.interfaces.distribution import IDistributionSet
from canonical.launchpad.interfaces.language import ILanguageSet
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import LaunchpadFunctionalLayer


class TestQuestionTarget(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def test_answer_contacts_with_languages_for_product_prefills_cache(self):
        answer_contact = self.factory.makePerson()
        login_person(answer_contact)
        product = self.factory.makeProduct()
        pt_br = getUtility(ILanguageSet)['pt_BR']
        answer_contact.addLanguage(pt_br)
        product.addAnswerContact(answer_contact)
        self.failIf(hasattr(answer_contact, '_languages_cache'))
        # Need to remove the product's security proxy because
        # answer_contacts_with_languages is not part of its public API.
        answer_contacts = removeSecurityProxy(
            product).answer_contacts_with_languages
        self.failUnlessEqual(answer_contacts, [answer_contact])
        self.failUnlessEqual(answer_contacts[0]._languages_cache, [pt_br])

    def test_answer_contacts_with_languages_for_package_prefills_cache(self):
        answer_contact = self.factory.makePerson()
        login_person(answer_contact)
        pt_br = getUtility(ILanguageSet)['pt_BR']
        answer_contact.addLanguage(pt_br)
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        self.factory.makeSourcePackageName(name='test-pkg')
        source_package = ubuntu.getSourcePackage('test-pkg')
        source_package.addAnswerContact(answer_contact)

        self.failIf(hasattr(answer_contact, '_languages_cache'))

        # Need to remove the sourcepackage's security proxy because
        # answer_contacts_with_languages is not part of its public API.
        answer_contacts = removeSecurityProxy(
            source_package).answer_contacts_with_languages
        self.failUnlessEqual(answer_contacts, [answer_contact])
        self.failUnlessEqual(answer_contacts[0]._languages_cache, [pt_br])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
