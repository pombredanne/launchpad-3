# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test questiontarget views."""

__metaclass__ = type

import os

from canonical.testing import DatabaseFunctionalLayer
from lp.testing import person_logged_in, TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestSearchQuestionsView(TestCaseWithFactory):
    """Test the behaviour of SearchQuestionsView."""

    layer = DatabaseFunctionalLayer

    def assertViewTemplate(self, context, file_name):
        view = create_initialized_view(context, '+questions')
        self.assertEqual(
            file_name, os.path.basename(view.template.filename))

    def test_template_product_official_answers_unknown(self):
        product = self.factory.makeProduct()
        self.assertViewTemplate(product, 'unknown-support.pt')

    def test_template_product_official_answers_launchpad(self):
        product = self.factory.makeProduct()
        with person_logged_in(product.owner) as owner:
            product.official_answers = True
        self.assertViewTemplate(product, 'question-listing.pt')

    def test_template_projectgroup_official_answers_unknown(self):
        product = self.factory.makeProduct()
        project_group = self.factory.makeProject(owner=product.owner)
        with person_logged_in(product.owner) as owner:
            product.project = project_group
        self.assertViewTemplate(project_group, 'unknown-support.pt')

    def test_template_projectgroup_official_answers_launchpad(self):
        product = self.factory.makeProduct()
        project_group = self.factory.makeProject(owner=product.owner)
        with person_logged_in(product.owner) as owner:
            product.project = project_group
            product.official_answers = True
        self.assertViewTemplate(project_group, 'question-listing.pt')

    def test_template_distribution_official_answers_unknown(self):
        distribution = self.factory.makeDistribution()
        self.assertViewTemplate(distribution, 'unknown-support.pt')

    def test_template_distribution_official_answers_launchpad(self):
        distribution = self.factory.makeDistribution()
        with person_logged_in(distribution.owner) as owner:
            distribution.official_answers = True
        self.assertViewTemplate(distribution, 'question-listing.pt')

    def test_template_DSP_official_answers_unknown(self):
        dsp = self.factory.makeDistributionSourcePackage()
        self.assertViewTemplate(dsp, 'unknown-support.pt')

    def test_template_DSP_official_answers_launchpad(self):
        dsp = self.factory.makeDistributionSourcePackage()
        with person_logged_in(dsp.distribution.owner) as owner:
            dsp.distribution.official_answers = True
        self.assertViewTemplate(dsp, 'question-listing.pt')

    def test_template_person(self):
        person = self.factory.makePerson()
        self.assertViewTemplate(person, 'question-listing.pt')
