# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)


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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
