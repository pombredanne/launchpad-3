# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the question module."""

__metaclass__ = type

__all__ = []

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.answers.browser.question import QuestionTargetWidget
from lp.answers.interfaces.question import IQuestion
from lp.answers.publisher import AnswersLayer
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestQuestionAddView(TestCaseWithFactory):
    """Verify the behavior of the QuestionAddView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestQuestionAddView, self).setUp()
        self.question_target = self.factory.makeProduct()
        self.user = self.factory.makePerson()
        login_person(self.user)

    def getSearchForm(self, title, language='en'):
        return {
            'field.title': title,
            'field.language': language,
            'field.actions.continue': 'Continue',
            }

    def test_question_title_within_max_display_width(self):
        # Titles (summary in the view) less than 250 characters are accepted.
        form = self.getSearchForm('123456789 ' * 10)
        view = create_initialized_view(
            self.question_target, name='+addquestion', layer=AnswersLayer,
            form=form, principal=self.user)
        self.assertEqual([], view.errors)

    def test_question_title_exceeds_max_display_width(self):
        # Titles (summary in the view) cannot exceed 250 characters.
        form = self.getSearchForm('123456789 ' * 26)
        view = create_initialized_view(
            self.question_target, name='+addquestion', layer=AnswersLayer,
            form=form, principal=self.user)
        self.assertEqual(1, len(view.errors))
        self.assertEqual(
            'The summary cannot exceed 250 characters.', view.errors[0])


class QuestionTargetWidgetTestCase(TestCaseWithFactory):
    """Test that QuestionTargetWidgetTestCase behaves as expected."""
    layer = DatabaseFunctionalLayer

    def getWidget(self, question):
        field = IQuestion['target']
        bound_field = field.bind(question)
        request = LaunchpadTestRequest()
        return QuestionTargetWidget(bound_field, request)

    def test_getDistributionVocabulary_with_product_question(self):
        # The vocabulary does not contain distros that do not use
        # launchpad to track answers.
        distribution = self.factory.makeDistribution()
        product = self.factory.makeProduct()
        question = self.factory.makeQuestion(target=product)
        target_widget = self.getWidget(question)
        vocabulary = target_widget.getDistributionVocabulary()
        self.assertEqual(None, vocabulary.distribution)
        self.assertFalse(
            distribution in vocabulary,
            "Vocabulary contains distros that do not use Launchpad Answers.")

    def test_getDistributionVocabulary_with_distribution_question(self):
        # The vocabulary does not contain distros that do not use
        # launchpad to track answers.
        distribution = self.factory.makeDistribution()
        other_distribution = self.factory.makeDistribution()
        question = self.factory.makeQuestion(target=distribution)
        target_widget = self.getWidget(question)
        vocabulary = target_widget.getDistributionVocabulary()
        self.assertEqual(distribution, vocabulary.distribution)
        self.assertTrue(
            distribution in vocabulary,
            "Vocabulary missing context distribution.")
        self.assertFalse(
            other_distribution in vocabulary,
            "Vocabulary contains distros that do not use Launchpad Answers.")
