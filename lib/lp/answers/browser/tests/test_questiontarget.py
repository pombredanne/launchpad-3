# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test questiontarget views."""

__metaclass__ = type

import os
from urllib import quote

from BeautifulSoup import BeautifulSoup
from zope.component import getUtility

from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.answers.interfaces.questioncollection import IQuestionSet
from lp.app.enums import ServiceUsage
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestSearchQuestionsView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_matching_faqs_url__handles_non_ascii(self):
        product = self.factory.makeProduct()
        # Avoid non-ascii character in unicode literal to not upset
        # pocket-lint. Bug #776389.
        non_ascii_string = u'portugu\xeas'
        with person_logged_in(product.owner):
            self.factory.makeFAQ(product, non_ascii_string)
        form = {
            'field.search_text': non_ascii_string,
            'field.status': 'OPEN',
            'field.actions.search': 'Search',
            }
        view = create_initialized_view(
            product, '+questions', form=form, method='GET')

        encoded_string = quote(non_ascii_string.encode('utf-8'))
        # This must not raise UnicodeEncodeError.
        self.assertIn(encoded_string, view.matching_faqs_url)


class TestSearchQuestionsViewCanConfigureAnswers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_cannot_configure_answers_product_no_edit_permission(self):
        product = self.factory.makeProduct()
        view = create_initialized_view(product, '+questions')
        self.assertEqual(False, view.can_configure_answers)

    def test_can_configure_answers_product_with_edit_permission(self):
        product = self.factory.makeProduct()
        login_person(product.owner)
        view = create_initialized_view(product, '+questions')
        self.assertEqual(True, view.can_configure_answers)

    def test_cannot_configure_answers_distribution_no_edit_permission(self):
        distribution = self.factory.makeDistribution()
        view = create_initialized_view(distribution, '+questions')
        self.assertEqual(False, view.can_configure_answers)

    def test_can_configure_answers_distribution_with_edit_permission(self):
        distribution = self.factory.makeDistribution()
        login_person(distribution.owner)
        view = create_initialized_view(distribution, '+questions')
        self.assertEqual(True, view.can_configure_answers)

    def test_cannot_configure_answers_projectgroup_with_edit_permission(self):
        # Project groups inherit Launchpad usage from their projects.
        project_group = self.factory.makeProject()
        login_person(project_group.owner)
        view = create_initialized_view(project_group, '+questions')
        self.assertEqual(False, view.can_configure_answers)

    def test_cannot_configure_answers_dsp_with_edit_permission(self):
        # DSPs inherit Launchpad usage from their distribution.
        dsp = self.factory.makeDistributionSourcePackage()
        login_person(dsp.distribution.owner)
        view = create_initialized_view(dsp, '+questions')
        self.assertEqual(False, view.can_configure_answers)


class TestSearchQuestionsViewTemplate(TestCaseWithFactory):
    """Test the behavior of SearchQuestionsView.template"""

    layer = DatabaseFunctionalLayer

    def assertViewTemplate(self, context, file_name):
        view = create_initialized_view(context, '+questions')
        self.assertEqual(
            file_name, os.path.basename(view.template.filename))

    def test_template_product_answers_usage_unknown(self):
        product = self.factory.makeProduct()
        self.assertViewTemplate(product, 'unknown-support.pt')

    def test_template_product_answers_usage_launchpad(self):
        product = self.factory.makeProduct()
        with person_logged_in(product.owner):
            product.answers_usage = ServiceUsage.LAUNCHPAD
        self.assertViewTemplate(product, 'question-listing.pt')

    def test_template_projectgroup_answers_usage_unknown(self):
        product = self.factory.makeProduct()
        project_group = self.factory.makeProject(owner=product.owner)
        with person_logged_in(product.owner):
            product.project = project_group
        self.assertViewTemplate(project_group, 'unknown-support.pt')

    def test_template_projectgroup_answers_usage_launchpad(self):
        product = self.factory.makeProduct()
        project_group = self.factory.makeProject(owner=product.owner)
        with person_logged_in(product.owner):
            product.project = project_group
            product.answers_usage = ServiceUsage.LAUNCHPAD
        self.assertViewTemplate(project_group, 'question-listing.pt')

    def test_template_distribution_answers_usage_unknown(self):
        distribution = self.factory.makeDistribution()
        self.assertViewTemplate(distribution, 'unknown-support.pt')

    def test_template_distribution_answers_usage_launchpad(self):
        distribution = self.factory.makeDistribution()
        with person_logged_in(distribution.owner):
            distribution.answers_usage = ServiceUsage.LAUNCHPAD
        self.assertViewTemplate(distribution, 'question-listing.pt')

    def test_template_DSP_answers_usage_unknown(self):
        dsp = self.factory.makeDistributionSourcePackage()
        self.assertViewTemplate(dsp, 'unknown-support.pt')

    def test_template_DSP_answers_usage_launchpad(self):
        dsp = self.factory.makeDistributionSourcePackage()
        with person_logged_in(dsp.distribution.owner):
            dsp.distribution.answers_usage = ServiceUsage.LAUNCHPAD
        self.assertViewTemplate(dsp, 'question-listing.pt')

    def test_template_question_set(self):
        question_set = getUtility(IQuestionSet)
        self.assertViewTemplate(question_set, 'question-listing.pt')


class TestSearchQuestionsViewUnknown(TestCaseWithFactory):
    """Test the behavior of SearchQuestionsView unknown support."""

    layer = DatabaseFunctionalLayer

    def linkPackage(self, product, name):
        # A helper to setup a legitimate Packaging link between a product
        # and an Ubuntu source package.
        hoary = getUtility(ILaunchpadCelebrities).ubuntu['hoary']
        sourcepackagename = self.factory.makeSourcePackageName(name)
        self.factory.makeSourcePackage(
            sourcepackagename=sourcepackagename, distroseries=hoary)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=sourcepackagename, distroseries=hoary)
        product.development_focus.setPackaging(
            hoary, sourcepackagename, product.owner)

    def setUp(self):
        super(TestSearchQuestionsViewUnknown, self).setUp()
        self.product = self.factory.makeProduct()
        self.view = create_initialized_view(self.product, '+questions')

    def assertCommonPageElements(self, content):
        robots = content.find('meta', attrs={'name': 'robots'})
        self.assertEqual('noindex,nofollow', robots['content'])
        self.assertTrue(content.find(True, id='support-unknown') is not None)

    def test_any_question_target_any_user(self):
        content = BeautifulSoup(self.view())
        self.assertCommonPageElements(content)

    def test_product_with_packaging_elements(self):
        self.linkPackage(self.product, 'cow')
        content = BeautifulSoup(self.view())
        self.assertCommonPageElements(content)
        self.assertTrue(content.find(True, id='ubuntu-support') is not None)

    def test_product_with_edit_permission(self):
        login_person(self.product.owner)
        self.view = create_initialized_view(
            self.product, '+questions', principal=self.product.owner)
        content = BeautifulSoup(self.view())
        self.assertCommonPageElements(content)
        self.assertTrue(
            content.find(True, id='configure-support') is not None)


class QuestionSetViewTestCase(TestCaseWithFactory):
    """Test the answers application root view."""

    layer = DatabaseFunctionalLayer

    def test_search_questions_form_rendering(self):
        # The view's template directly renders the form widgets.
        question_set = getUtility(IQuestionSet)
        view = create_initialized_view(question_set, '+index')
        content = find_tag_by_id(view.render(), 'search-all-questions')
        self.assertEqual('form', content.name)
        self.assertIsNot(None, content.find(True, id='text'))
        self.assertIsNot(
            None, content.find(True, id='field.actions.search'))
        self.assertIsNot(
            None, content.find(True, id='field.scope.option.all'))
        self.assertIsNot(
            None, content.find(True, id='field.scope.option.project'))
        target_widget = view.widgets['scope'].target_widget
        self.assertIsNot(
            None, content.find(True, id=target_widget.show_widget_id))
        text = str(content)
        picker_script = (
            "vocabulary_name: 'DistributionOrProductOrProjectGroup'")
        self.assertIn(picker_script, text)
        focus_script = "setFocusByName('field.search_text')"
        self.assertIn(focus_script, text)
