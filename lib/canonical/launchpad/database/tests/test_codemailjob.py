# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests of CodeMailJob"""

__metaclass__ = type

from datetime import datetime
import unittest

from canonical.testing import LaunchpadFunctionalLayer
import pytz

from canonical.launchpad.database import CodeMailJobSource, Job
from canonical.launchpad.interfaces import ICodeMailJob, JobStatus
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.tests.mail_helpers import pop_notifications
from canonical.launchpad.webapp.testing import verifyObject


class TestCodeMailJob(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_ProvidesInterface(self):
        verifyObject(ICodeMailJob, self.factory.makeCodeMailJob())

    def makeExampleMail(self):
        UTC = pytz.timezone('UTC')
        return self.factory.makeCodeMailJob('jrandom@example.com',
            'person@example.com', 'My subject', 'My body', 'My footer',
            '<msg-id@foo>', 'for-fun', 'http://example.com', 'Project',
            '<parent-id@foo>', '<mp1@example.com>',
            datetime.fromtimestamp(0, UTC))

    def test_toMessage(self):
        mail_job = self.makeExampleMail()
        message = mail_job.toMessage()
        self.checkMessageFromExample(message)

    def checkMessageFromExample(self, message):
        self.assertEqual('jrandom@example.com', message['To'])
        self.assertEqual('person@example.com', message['From'])
        self.assertEqual('<mp1@example.com>', message['Reply-To'])
        self.assertEqual('for-fun', message['X-Launchpad-Message-Rationale'])
        self.assertEqual('http://example.com', message['X-Launchpad-Branch'])
        self.assertEqual('Project', message['X-Launchpad-Project'])
        self.assertEqual('<msg-id@foo>', message['Message-Id'])
        self.assertEqual('<parent-id@foo>', message['In-Reply-To'])
        self.assertEqual('My subject', message['Subject'])
        self.assertEqual('Thu, 01 Jan 1970 00:00:00 -0000', message['Date'])
        self.assertEqual(
            'My body\n-- \nMy footer', message.get_payload(decode=True))

    def test_run(self):
        """Test that running a job works."""
        mail_job = self.makeExampleMail()
        db_id = mail_job.id
        mail_job.run()
        message = pop_notifications()[0]
        self.checkMessageFromExample(message)
        self.assertEqual(JobStatus.COMPLETED, mail_job.job.status)

    def testFindRunnableJobs(self):
        """Test that findRunnableJobs finds the right jobs.

        mail_job1 is WAITING, and its prerequisites are all in terminal
        states.
        """
        mail_job1 = self.makeExampleMail()
        mail_job1.job.addPrerequisite(Job(status=JobStatus.COMPLETED))
        mail_job1.job.addPrerequisite(Job(status=JobStatus.FAILED))
        mail_job2 = self.makeExampleMail()
        mail_job2.job.status = JobStatus.COMPLETED
        mail_job3 = self.makeExampleMail()
        mail_job3.job.addPrerequisite(Job())
        self.assertEqual(
            [mail_job1], list(CodeMailJobSource.findRunnableJobs()))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
