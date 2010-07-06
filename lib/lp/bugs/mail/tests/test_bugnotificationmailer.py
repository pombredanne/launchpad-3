# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `BugNotificationMailer` code."""

__metaclass__ = type

import unittest

from canonical.testing import DatabaseFunctionalLayer

from lp.bugs.model.bugnotification import BugNotification
from lp.bugs.mail.bugnotificationmailer import BugNotificationMailer
from lp.testing import TestCaseWithFactory


class TestBugNotificationMailerHeaders(TestCaseWithFactory):
    """Tests for headers produced by the BugNotificationMailer class."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugNotificationMailerHeaders, self).setUp(
            user='test@canonical.com')

        self.notification_recipient = self.factory.makePerson()
        self.person = self.factory.makePerson()

    def test_bug_creation(self):
        bug = self.factory.makeBug(owner=self.person)
        notification = BugNotification.selectFirst(orderBy='-id')
        mailer = BugNotificationMailer(notification, 'bug-notification.txt')
        headers = mailer._getHeaders()

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
