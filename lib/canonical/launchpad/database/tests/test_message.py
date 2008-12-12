# Copyright 2004-2005, 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from email.Message import Message
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.Utils import formatdate, make_msgid
import transaction
import unittest

from canonical.testing import LaunchpadFunctionalLayer
from zope.testing.doctestunit import DocTestSuite

from canonical.launchpad.database import MessageSet
from canonical.launchpad.ftests import login
from canonical.launchpad.testing import LaunchpadObjectFactory


class TestMessageSet(unittest.TestCase):
    """Test the methods of `MessageSet`."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        unittest.TestCase.setUp(self)
        # Testing behavior, not permissions here.
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()

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
        transaction.commit()
        self.assertEqual('This is the diff, honest.', diff.blob.read())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(DocTestSuite('canonical.launchpad.database.message'))
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite

if __name__ == '__main__':
    unittest.main(test_suite())

