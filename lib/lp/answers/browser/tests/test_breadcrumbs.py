# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)

from lp.testing import login_person


class TestQuestionTargetProjectAndPersonBreadcrumbOnAnswersVHost(
        BaseBreadcrumbTestCase):
    """Test Breadcrumbs for IQuestionTarget, IProject and IPerson on the
    answers vhost.

    Any page below them on the answers vhost will get an extra breadcrumb for
    their homepage on the answers vhost, right after the breadcrumb for their
    mainsite homepage.
    """

    def setUp(self):
        super(TestQuestionTargetProjectAndPersonBreadcrumbOnAnswersVHost,
              self).setUp()
        self.person = self.factory.makePerson()
        self.person_questions_url = canonical_url(
            self.person, rootsite='answers')
        self.product = self.factory.makeProduct()
        self.product_questions_url = canonical_url(
            self.product, rootsite='answers')
        self.project = self.factory.makeProject()
        self.project_questions_url = canonical_url(
            self.project, rootsite='answers')

    def test_product(self):
        crumbs = self._getBreadcrumbs(
            self.product_questions_url, [self.root, self.product])
        last_crumb = crumbs[-1]
        self.assertEquals(last_crumb.url, self.product_questions_url)
        self.assertEquals(last_crumb.text, 'Questions')

    def test_project(self):
        crumbs = self._getBreadcrumbs(
            self.project_questions_url, [self.root, self.project])
        last_crumb = crumbs[-1]
        self.assertEquals(last_crumb.url, self.project_questions_url)
        self.assertEquals(last_crumb.text, 'Questions')

    def test_person(self):
        crumbs = self._getBreadcrumbs(
            self.person_questions_url, [self.root, self.person])
        last_crumb = crumbs[-1]
        self.assertEquals(last_crumb.url, self.person_questions_url)
        self.assertEquals(last_crumb.text, 'Questions')


class TestAnswersBreadcrumb(BaseBreadcrumbTestCase):
    """Test Breadcrumbs for answer module objects."""

    def setUp(self):
        super(TestAnswersBreadcrumb, self).setUp()
        self.product = self.factory.makeProduct(name="mellon")
        login_person(self.product.owner)
        self.question = self.factory.makeQuestion(
            target=self.product, title='Seeds are hard to chew')
        self.question_url = canonical_url(self.question, rootsite='answers')
        self.faq = self.factory.makeFAQ(target=self.product, title='Seedless')
        self.faq_url = canonical_url(self.faq, rootsite='answers')

    def test_question(self):
        crumbs = self._getBreadcrumbs(
            self.question_url, [self.root, self.product, self.question])
        last_crumb = crumbs[-1]
        self.assertEquals(last_crumb.text, 'Question #%d' % self.question.id)

    def test_faq(self):
        crumbs = self._getBreadcrumbs(
            self.faq_url, [self.root, self.product, self.faq])
        last_crumb = crumbs[-1]
        self.assertEquals(last_crumb.text, 'FAQ #%d' % self.faq.id)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
