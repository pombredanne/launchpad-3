# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `BugNotificationMailer` code."""

__metaclass__ = type

import unittest

from canonical.testing import DatabaseFunctionalLayer

from lp.bugs.model.bugnotification import BugNotification
from lp.bugs.mail.bugnotificationbuilder import get_bugmail_replyto_address
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

        mailer.message_id = '<foobar-example-com>'
        generated_mail = mailer.generateEmail(
            bug.owner.preferredemail.email, bug.owner)

        expected_headers = {
            'Sender': 'bounces@canonical.com',
            'X-Launchpad-Bug-Commenters': u'%s' % self.person.name,
            'X-Launchpad-Bug-Private': 'no',
            'X-Launchpad-Bug-Reporter':
                u'%s (%s)' % (self.person.displayname, self.person.name),
            'X-Launchpad-Bug': [
                u'product=%s; status=New; '
                u'importance=Undecided; assignee=None;' % (
                    bug.bugtasks[0].product.name),
                ],
            'Reply-To': get_bugmail_replyto_address(bug),
            'X-Launchpad-Bug-Security-Vulnerability': 'no',
            }
        self.assertEqual(expected_headers, generated_mail.headers)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
