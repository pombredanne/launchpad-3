# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from cStringIO import StringIO
from doctest import DocTestSuite
from email.Message import Message
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Utils import (
    formatdate,
    make_msgid,
    )
import unittest

from sqlobject import SQLObjectNotFound
from zope.component import getUtility

from canonical.launchpad.database.message import (
    MessageJob,
    MessageJobAction,
    MessageSet,
    )
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.message import IMessageJob
from canonical.launchpad.webapp.testing import verifyObject
from canonical.librarian.testing.fake import FakeLibrarian
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.services.job.model.job import Job
from lp.services.mail.sendmail import MailController
from lp.testing import TestCaseWithFactory


class TestMessageSet(TestCaseWithFactory):
    """Test the methods of `MessageSet`."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        # Testing behavior, not permissions here.
        super(TestMessageSet, self).setUp(user='admin@canonical.com')
        self.fake_librarian = self.useFixture(FakeLibrarian())

    def createTestMessages(self):
        """Create some test messages."""
        message1 = self.factory.makeMessage()
        message2 = self.factory.makeMessage(parent=message1)
        message3 = self.factory.makeMessage(parent=message1)
        message4 = self.factory.makeMessage(parent=message2)
        return (message1, message2, message3, message4)

    def test_parentToChild(self):
        """Test MessageSet._parentToChild."""
        messages = self.createTestMessages()
        message1, message2, message3, message4 = messages
        expected = {
            message1: [message2, message3],
            message2: [message4],
            message3: [], message4:[]}
        result, roots = MessageSet._parentToChild(messages)
        self.assertEqual(expected, result)
        self.assertEqual([message1], roots)

    def test_threadMessages(self):
        """Test MessageSet.threadMessages."""
        messages = self.createTestMessages()
        message1, message2, message3, message4 = messages
        threads = MessageSet.threadMessages(messages)
        self.assertEqual(
            [(message1, [(message2, [(message4, [])]), (message3, [])])],
            threads)

    def test_flattenThreads(self):
        """Test MessageSet.flattenThreads."""
        messages = self.createTestMessages()
        message1, message2, message3, message4 = messages
        threads = MessageSet.threadMessages(messages)
        flattened = list(MessageSet.flattenThreads(threads))
        expected = [(0, message1),
                    (1, message2),
                    (2, message4),
                    (1, message3)]
        self.assertEqual(expected, flattened)

    def test_fromEmail_keeps_attachments(self):
        """Test that the parsing of the email keeps the attachments."""
        # Build a simple multipart message with a plain text first part
        # and an text/x-diff attachment.
        sender = self.factory.makePerson()
        msg = MIMEMultipart()
        msg['Message-Id'] = make_msgid('launchpad')
        msg['Date'] = formatdate()
        msg['To'] = 'to@example.com'
        msg['From'] = sender.preferredemail.email
        msg['Subject'] = 'Sample'
        msg.attach(MIMEText('This is the body of the email.'))
        attachment = Message()
        attachment.set_payload('This is the diff, honest.')
        attachment['Content-Type'] = 'text/x-diff'
        attachment['Content-Disposition'] = (
            'attachment; filename="review.diff"')
        msg.attach(attachment)
        # Now create the message from the MessageSet.
        message = MessageSet().fromEmail(msg.as_string())
        text, diff = message.chunks
        self.assertEqual('This is the body of the email.', text.content)
        self.assertEqual('review.diff', diff.blob.filename)
        self.assertEqual('text/x-diff', diff.blob.mimetype)
        # Need to commit in order to read back out of the librarian.
        self.fake_librarian.pretendCommit()
        self.assertEqual('This is the diff, honest.', diff.blob.read())

    def test_fromEmail_strips_attachment_paths(self):
        # Build a simple multipart message with a plain text first part
        # and an text/x-diff attachment.
        sender = self.factory.makePerson()
        msg = MIMEMultipart()
        msg['Message-Id'] = make_msgid('launchpad')
        msg['Date'] = formatdate()
        msg['To'] = 'to@example.com'
        msg['From'] = sender.preferredemail.email
        msg['Subject'] = 'Sample'
        msg.attach(MIMEText('This is the body of the email.'))
        attachment = Message()
        attachment.set_payload('This is the diff, honest.')
        attachment['Content-Type'] = 'text/x-diff'
        attachment['Content-Disposition'] = (
            'attachment; filename="/tmp/foo/review.diff"')
        msg.attach(attachment)
        # Now create the message from the MessageSet.
        message = MessageSet().fromEmail(msg.as_string())
        text, diff = message.chunks
        self.assertEqual('This is the body of the email.', text.content)
        self.assertEqual('review.diff', diff.blob.filename)
        self.assertEqual('text/x-diff', diff.blob.mimetype)
        # Need to commit in order to read back out of the librarian.
        self.fake_librarian.pretendCommit()
        self.assertEqual('This is the diff, honest.', diff.blob.read())


class TestMessageJob(TestCaseWithFactory):
    """Tests for MessageJob."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestMessageJob, self).setUp()
        self.fake_librarian = self.useFixture(FakeLibrarian())

    def test_providesInterface(self):
        """Ensure that BranchJob implements IBranchJob."""
        # Ensure database constraints are satisfied.
        file_alias = self.factory.makeMergeDirectiveEmail()[1]
        job = MessageJob(file_alias, MessageJobAction.CREATE_MERGE_PROPOSAL)
        job.sync()
        verifyObject(IMessageJob, job)

    def test_destroySelf_destroys_job(self):
        """Ensure that MessageJob.destroySelf destroys the Job as well."""
        file_alias = self.factory.makeMergeDirectiveEmail()[1]
        message_job = MessageJob(
            file_alias, MessageJobAction.CREATE_MERGE_PROPOSAL)
        job_id = message_job.job.id
        message_job.destroySelf()
        self.assertRaises(SQLObjectNotFound, Job.get, job_id)

    def test_getMessage(self):
        """getMessage should return a Message with appropriate values."""
        ctrl = MailController(
            'from@example.com', ['to@example.com'], 'subject', 'body')
        content = ctrl.makeMessage().as_string()
        lfa = getUtility(ILibraryFileAliasSet).create(
            'message', len(content), StringIO(content), 'text/x-diff')
        message_job = MessageJob(lfa, MessageJobAction.CREATE_MERGE_PROPOSAL)
        self.fake_librarian.pretendCommit()
        message = message_job.getMessage()
        self.assertEqual('from@example.com', message['From'])
        self.assertEqual('to@example.com', message['To'])
        self.assertEqual('subject', message['Subject'])
        self.assertEqual('body', message.get_payload())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(DocTestSuite('canonical.launchpad.database.message'))
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite

if __name__ == '__main__':
    unittest.main(test_suite())

