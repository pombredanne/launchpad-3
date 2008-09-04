# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests of PendingCodeMail"""

__metaclass__ = type

from datetime import datetime
import unittest

from canonical.testing import LaunchpadFunctionalLayer
import pytz
from sqlobject import SQLObjectNotFound

from canonical.launchpad.interfaces import IPendingCodeMail
from canonical.launchpad.database import PendingCodeMail
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.tests.mail_helpers import pop_notifications
from canonical.launchpad.webapp.testing import verifyObject


class TestPendingCodeMail(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_ProvidesInterface(self):
        verifyObject(IPendingCodeMail, self.factory.makePendingCodeMail())

    def makeExampleMail(self):
        UTC = pytz.timezone('UTC')
        return self.factory.makePendingCodeMail('jrandom@example.com',
            'person@example.com', 'My subject', 'My body', 'My footer',
            '<msg-id@foo>', 'for-fun', 'http://example.com',
            '<parent-id@foo>', datetime.fromtimestamp(0, UTC))

    def test_toMessage(self):
        pending_mail = self.makeExampleMail()
        message = pending_mail.toMessage()
        self.checkMessageFromExample(message)

    def checkMessageFromExample(self, message):
        self.assertEqual('jrandom@example.com', message['To'])
        self.assertEqual('person@example.com', message['From'])
        self.assertEqual('for-fun', message['X-Launchpad-Message-Rationale'])
        self.assertEqual('http://example.com', message['X-Launchpad-Branch'])
        self.assertEqual('<msg-id@foo>', message['Message-Id'])
        self.assertEqual('<parent-id@foo>', message['In-Reply-To'])
        self.assertEqual('My subject', message['Subject'])
        self.assertEqual('Thu, 01 Jan 1970 00:00:00 -0000', message['Date'])
        self.assertEqual(
            'My body\n-- \nMy footer', message.get_payload(decode=True))

    def testSend(self):
        pending_mail = self.makeExampleMail()
        db_id = pending_mail.id
        pending_mail.sendMail()
        message = pop_notifications()[0]
        self.checkMessageFromExample(message)
        self.assertRaises(SQLObjectNotFound, PendingCodeMail.get, db_id)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
