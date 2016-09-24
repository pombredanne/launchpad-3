# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from testtools.testcase import ExpectedException
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import (
    admin_logged_in,
    anonymous_logged_in,
    celebrity_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestQuestionSecurity(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_title_and_description_writes(self):
        question = self.factory.makeQuestion()
        with anonymous_logged_in():
            with ExpectedException(Unauthorized):
                question.title = 'foo anon'
            with ExpectedException(Unauthorized):
                question.description = 'foo anon'
        with person_logged_in(self.factory.makePerson()):
            with ExpectedException(Unauthorized):
                question.title = 'foo random'
            with ExpectedException(Unauthorized):
                question.description = 'foo random'
        answer_contact = self.factory.makePerson()
        with person_logged_in(answer_contact):
            answer_contact.addLanguage(getUtility(ILanguageSet)['en'])
            question.target.addAnswerContact(answer_contact, answer_contact)
            with ExpectedException(Unauthorized):
                question.title = 'foo contact'
            with ExpectedException(Unauthorized):
                question.description = 'foo contact'
        with person_logged_in(question.owner):
            question.title = question.description = 'foo owner'
        with person_logged_in(question.target.owner):
            question.title = question.description = 'foo target owner'
        with admin_logged_in():
            question.title = question.description = 'foo admin'
        with celebrity_logged_in('registry_experts'):
            question.title = question.description = 'foo registry'


class TestQuestionSearch(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_projectgroup_with_inactive_products_not_in_results(self):
        group = self.factory.makeProject()
        product = self.factory.makeProduct(projectgroup=group)
        inactive = self.factory.makeProduct(projectgroup=group)
        question = self.factory.makeQuestion(target=product)
        self.factory.makeQuestion(target=inactive)
        removeSecurityProxy(inactive).active = False
        self.assertContentEqual([question], group.searchQuestions())
