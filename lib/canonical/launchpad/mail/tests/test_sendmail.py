# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.testing.doctest import DocTestSuite

from canonical.launchpad.testing import TestCase
from canonical.launchpad.mail.sendmail import MailController


class TestMailController(TestCase):

    def test_constructor(self):
        """Test the default construction behavior.

        Defaults should be empty.  The 'to' should be converted to a list.
        """
        ctrl = MailController(
            'from@example.com', 'to@example.com', 'subject', 'body')
        self.assertEqual('from@example.com', ctrl.from_addr)
        self.assertEqual(['to@example.com'], ctrl.to_addrs)
        self.assertEqual('subject', ctrl.subject)
        self.assertEqual({}, ctrl.headers)
        self.assertEqual('body', ctrl.body)
        self.assertEqual([], ctrl.attachments)

    def test_constructor2(self):
        """Test the explicit construction behavior.

        Since to is a list, it is not converted into a list.
        """
        ctrl = MailController(
            'from@example.com', ['to1@example.com', 'to2@example.com'],
            'subject', 'body', {'key': 'value'})
        self.assertEqual(
            ['to1@example.com', 'to2@example.com'], ctrl.to_addrs)
        self.assertEqual({'key': 'value'}, ctrl.headers)
        self.assertEqual('body', ctrl.body)
        self.assertEqual([], ctrl.attachments)

    def test_addAttachment(self):
        """addAttachment should add a part to the list of attachments."""
        ctrl = MailController(
            'from@example.com', 'to@example.com', 'subject', 'body')
        ctrl.addAttachment('content1')
        attachment = ctrl.attachments[0]
        self.assertEqual(
            'application/octet-stream', attachment['Content-Type'])
        self.assertEqual(
            'attachment', attachment['Content-Disposition'])
        self.assertEqual(
            'content1', attachment.get_payload(decode=True))
        ctrl.addAttachment(
            'content2', 'text/plain', inline=True, filename='name1')
        attachment = ctrl.attachments[1]
        self.assertEqual(
            'text/plain', attachment['Content-Type'])
        self.assertEqual(
            'inline; filename="name1"', attachment['Content-Disposition'])
        self.assertEqual(
            'content2', attachment.get_payload(decode=True))
        ctrl.addAttachment(
            'content2', 'text/plain', inline=True, filename='name1')

    def test_MakeMessageSpecialChars(self):
        """A message should have its to and from addrs converted to ascii."""
        to_addr = u'\u1100to@example.com'
        from_addr = u'\u1100from@example.com'
        ctrl = MailController(from_addr, to_addr, 'subject', 'body')
        message = ctrl.makeMessage()
        self.assertEqual('=?utf-8?b?4YSAZnJvbUBleGFtcGxlLmNvbQ==?=',
            message['From'])
        self.assertEqual('=?utf-8?b?4YSAdG9AZXhhbXBsZS5jb20=?=',
            message['To'])
        self.assertEqual('subject', message['Subject'])
        self.assertEqual('body', message.get_payload(decode=True))

    def test_MakeMessage_no_attachment(self):
        """A message without an attachment should have a single body."""
        ctrl = MailController(
            'from@example.com', 'to@example.com', 'subject', 'body')
        message = ctrl.makeMessage()
        self.assertEqual('from@example.com', message['From'])
        self.assertEqual('to@example.com', message['To'])
        self.assertEqual('subject', message['Subject'])
        self.assertEqual('body', message.get_payload(decode=True))

    def test_MakeMessage_unicode_body(self):
        # A message without an attachment with a unicode body gets sent as
        # UTF-8 encoded MIME text, and the message as a whole can be flattened
        # to a string with Unicode errors.
        ctrl = MailController(
            'from@example.com', 'to@example.com', 'subject', u'Bj\xf6rn')
        message = ctrl.makeMessage()
        # Make sure that the message can be flattened to a string as sendmail
        # does without raising a UnicodeEncodeError.
        message.as_string()
        self.assertEqual('Bj\xc3\xb6rn', message.get_payload(decode=True))

    def test_MakeMessage_unicode_body_with_attachment(self):
        # A message with an attachment with a unicode body gets sent as
        # UTF-8 encoded MIME text, and the message as a whole can be flattened
        # to a string with Unicode errors.
        ctrl = MailController(
            'from@example.com', 'to@example.com', 'subject', u'Bj\xf6rn')
        ctrl.addAttachment('attach')
        message = ctrl.makeMessage()
        # Make sure that the message can be flattened to a string as sendmail
        # does without raising a UnicodeEncodeError.
        message.as_string()
        body, attachment = message.get_payload()
        self.assertEqual('Bj\xc3\xb6rn', body.get_payload(decode=True))

    def test_MakeMessage_with_attachment(self):
        """A message with an attachment should be multipart."""
        ctrl = MailController(
            'from@example.com', 'to@example.com', 'subject', 'body')
        ctrl.addAttachment('attach')
        message = ctrl.makeMessage()
        self.assertEqual('from@example.com', message['From'])
        self.assertEqual('to@example.com', message['To'])
        self.assertEqual('subject', message['Subject'])
        body, attachment = message.get_payload()
        self.assertEqual('body', body.get_payload(decode=True))
        self.assertEqual('attach', attachment.get_payload(decode=True))
        self.assertEqual(
            'application/octet-stream', attachment['Content-Type'])
        self.assertEqual('attachment', attachment['Content-Disposition'])

    def test_MakeMessage_with_specific_attachment(self):
        """Explicit attachment params should be obeyed."""
        ctrl = MailController(
            'from@example.com', 'to@example.com', 'subject', 'body')
        ctrl.addAttachment(
            'attach', 'text/plain', inline=True, filename='README')
        message = ctrl.makeMessage()
        attachment = message.get_payload()[1]
        self.assertEqual('attach', attachment.get_payload(decode=True))
        self.assertEqual(
            'text/plain', attachment['Content-Type'])
        self.assertEqual(
            'inline; filename="README"', attachment['Content-Disposition'])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('canonical.launchpad.mail.sendmail'))
    suite.addTests(unittest.TestLoader().loadTestsFromName(__name__))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
