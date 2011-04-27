# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for QuestionJobs classes."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from lp.answers.enums import QuestionJobType
from lp.answers.model.questionjob import (
    QuestionJob,
    QuestionEmailJob,
    )
from lp.testing import TestCaseWithFactory


class QuestionJobTestCase(TestCaseWithFactory):
    """Test case for base QuestionJob class."""

    layer = DatabaseFunctionalLayer

    def test_instantiate(self):
        question = self.factory.makeQuestion()
        metadata = ('some', 'arbitrary', 'metadata')
        job = QuestionJob(
            question, QuestionJobType.EMAIL, metadata)
        self.assertEqual(QuestionJobType.EMAIL, job.job_type)
        self.assertEqual(question, job.question)
        # Metadata is unserialized from JSON.
        metadata_expected = list(metadata)
        self.assertEqual(metadata_expected, job.metadata)

    def test_repr(self):
        question = self.factory.makeQuestion()
        metadata = []
        question_job = QuestionJob(
            question, QuestionJobType.EMAIL, metadata)
        self.assertEqual(
            '<QuestionJob for question %s; status=Waiting>' % question.id,
            repr(question_job))


class QuestionEmailJobTestCase(TestCaseWithFactory):
    """Test case for QuestionEmailJob class."""

    layer = DatabaseFunctionalLayer

    def test_create(self):
        question = self.factory.makeQuestion()
        user = self.factory.makePerson()
        body = 'email body'
        headers = {'X-Launchpad-Question': 'question metadata'}
        job = QuestionEmailJob.create(question, user, body, headers)
        self.assertEqual(QuestionJobType.EMAIL, job.job_type)
        self.assertEqual(question, job.question)
        self.assertEqual(
            ['body', 'headers', 'user'], sorted(job.metadata.keys()))
        self.assertEqual(user.id, job.metadata['user'])
        self.assertEqual(body, job.metadata['body'])
        self.assertEqual(
            headers['X-Launchpad-Question'],
            job.metadata['headers']['X-Launchpad-Question'])
