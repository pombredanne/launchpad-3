# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for QuestionJobs classes."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from lp.answers.enums import QuestionJobType
from lp.answers.model.questionjob import QuestionJob
from lp.testing import TestCaseWithFactory


class QuestionJobTestCase(TestCaseWithFactory):
    """Test case for base QuestionJob class."""

    layer = DatabaseFunctionalLayer

    def test_instantiate(self):
        question = self.factory.makeQuestion()
        metadata = ('some', 'arbitrary', 'metadata')
        question_job = QuestionJob(
            question, QuestionJobType.EMAIL, metadata)
        self.assertEqual(QuestionJobType.EMAIL, question_job.job_type)
        self.assertEqual(question, question_job.question)
        # Metadata is unserialized from JSON.
        metadata_expected = list(metadata)
        self.assertEqual(metadata_expected, question_job.metadata)

    def test_repr(self):
        question = self.factory.makeQuestion()
        metadata = []
        question_job = QuestionJob(
            question, QuestionJobType.EMAIL, metadata)
        self.assertEqual(
            '<QuestionJob for question %s; status=Waiting>' % question.id,
            repr(question_job))
