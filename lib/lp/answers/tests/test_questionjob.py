# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for QuestionJobs classes."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.mail import format_address
from canonical.testing import DatabaseFunctionalLayer
from lp.answers.enums import QuestionJobType
from lp.answers.model.questionjob import (
    QuestionJob,
    QuestionEmailJob,
    )
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


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

    def makeUserSubjectBodyHeaders(self):
        user = self.factory.makePerson()
        subject = 'email subject'
        body = 'email body'
        headers = {'X-Launchpad-Question': 'question metadata'}
        return user, subject, body, headers

    def test_create(self):
        # The create class method converts the extra job arguments
        # to metadata.
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        self.assertEqual(QuestionJobType.EMAIL, job.job_type)
        self.assertEqual(question, job.question)
        self.assertEqual(
            ['body', 'headers', 'subject', 'user'],
            sorted(job.metadata.keys()))
        self.assertEqual(user.id, job.metadata['user'])
        self.assertEqual(subject, job.metadata['subject'])
        self.assertEqual(body, job.metadata['body'])
        self.assertEqual(
            headers['X-Launchpad-Question'],
            job.metadata['headers']['X-Launchpad-Question'])

    def test_iterReady(self):
        # Jobs in the ready state are returned by the iterator.
        question = self.factory.makeQuestion()
        user, subject, ignore, headers = self.makeUserSubjectBodyHeaders()
        job_1 = QuestionEmailJob.create(
            question, user, subject, 'one', headers)
        job_2 = QuestionEmailJob.create(
            question, user, subject, 'two', headers)
        job_3 = QuestionEmailJob.create(
            question, user, subject, 'three', headers)
        job_1.start()
        job_1.complete()
        job_ids = sorted(job.id for job in QuestionEmailJob.iterReady())
        self.assertEqual(sorted([job_2.id, job_3.id]), job_ids)

    def test_user(self):
        # The user property matches the user passed to create().
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        self.assertEqual(user, job.user)

    def test_subject(self):
        # The subject property matches the subject passed to create().
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        self.assertEqual(body, job.body)

    def test_body(self):
        # The body property matches the body passed to create().
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        self.assertEqual(body, job.body)

    def test_headers(self):
        # The headers property matches the headers passed to create().
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        self.assertEqual(headers, job.headers)

    def test_from_address(self):
        # The from_address is the question with the user displayname.
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        address = format_address(
            user.displayname,
            "question%s@answers.launchpad.net" % question.id)
        self.assertEqual(address, job.from_address)

    def test_log_name(self):
        # The log_name property matches the class name.
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        self.assertEqual(job.__class__.__name__, job.log_name)

    def test_getOopsVars(self):
        # The getOopsVars() method adds the question and user to the vars.
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        oops_vars = job.getOopsVars()
        self.assertTrue(('question', question.id) in oops_vars)
        self.assertTrue(('user', user.name) in oops_vars)

    def test_getErrorRecipients(self):
        # The getErrorRecipients method matches the user.
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        self.assertEqual(user, job.getErrorRecipients())

    def test_recipients(self):
        # The recipients property mathes the question recipients.
        question = self.factory.makeQuestion()
        user, subject, body, headers = self.makeUserSubjectBodyHeaders()
        job = QuestionEmailJob.create(question, user, subject, body, headers)
        contact = self.factory.makePerson()
        with person_logged_in(contact):
            lang_set = getUtility(ILanguageSet)
            contact.addLanguage(lang_set['en'])
            question.target.addAnswerContact(contact)
        self.assertEqual(question.getRecipients(), job.recipients)

    def test_run(self):
        # The email is sent to all the recipents.
        pass
