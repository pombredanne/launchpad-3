# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `BugNotificationMailer` code."""

__metaclass__ = type

import unittest

from canonical.testing import DatabaseFunctionalLayer

from lp.bugs.interfaces.bugtask import BugTaskImportance, BugTaskStatus
from lp.bugs.model.bugnotification import BugNotification
from lp.bugs.mail.bugnotificationbuilder import get_bugmail_replyto_address
from lp.bugs.mail.bugnotificationmailer import BugNotificationMailer
from lp.testing import login, logout, TestCaseWithFactory


class TestBugNotificationMailerHeaders(TestCaseWithFactory):
    """Tests for headers produced by the BugNotificationMailer class."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugNotificationMailerHeaders, self).setUp()
        self.notification_recipient = self.factory.makePerson()
        self.person = self.factory.makePerson()
        self.product = self.factory.makeProduct(owner=self.person)
        self.bug = self.factory.makeBug(
            owner=self.person, product=self.product)

        # We log in as self.person so that we can change things in the
        # test.
        login(self.person.preferredemail.email)

    def _getExpectedHeaders(self, bug=None):
        """Return a dict of expected headers for a bug."""
        if bug is None:
            bug = self.bug

        expected_headers = {
            'Sender': 'bounces@canonical.com',
            'X-Launchpad-Bug-Commenters': u'%s' % bug.owner.name,
            'X-Launchpad-Bug-Private': 'no',
            'X-Launchpad-Bug-Reporter':
                u'%s (%s)' % (bug.owner.displayname, bug.owner.name),
            'X-Launchpad-Bug': [
                u'product=%s; status=New; '
                u'importance=Undecided; assignee=None;' % (
                    bug.bugtasks[0].product.name),
                ],
            'Reply-To': get_bugmail_replyto_address(bug),
            'X-Launchpad-Bug-Security-Vulnerability': 'no',
            'X-Launchpad-Message-Rationale': 'Subscriber',
            }
        return expected_headers

    def test_bug_creation(self):
        # The first notification should be the creation notification for
        # the new bug.
        notification = BugNotification.selectFirst(orderBy='-id')
        mailer = BugNotificationMailer(notification, 'bug-notification.txt')

        mailer.message_id = '<foobar-example-com>'
        generated_mail = mailer.generateEmail(
            self.bug.owner.preferredemail.email, self.bug.owner)

        expected_headers = self._getExpectedHeaders()
        self.assertEqual(expected_headers, generated_mail.headers)

    def test_bugtask_changed(self):
        # When a bugtask is changed, the Bug's headers will remain
        # unchanged except for those pertaining to the changed task.
        self.bug.bugtasks[0].transitionToStatus(
            BugTaskStatus.CONFIRMED, self.person)
        self.bug.bugtasks[0].transitionToAssignee(self.person)
        self.bug.bugtasks[0].transitionToImportance(
            BugTaskImportance.HIGH, self.person)

        notification = BugNotification.selectFirst(orderBy='-id')
        mailer = BugNotificationMailer(notification, 'bug-notification.txt')
        mailer.message_id = '<foobar-example-com>'
        generated_mail = mailer.generateEmail(
            self.bug.owner.preferredemail.email, self.bug.owner)

        expected_headers = self._getExpectedHeaders()
        expected_headers['X-Launchpad-Bug'] = [
            u'product=%s; status=Confirmed; '
            u'importance=High; assignee=%s;' % (
                self.bug.bugtasks[0].product.name,
                self.person.preferredemail.email),
            ]
        self.assertEqual(expected_headers, generated_mail.headers)

    def test_bugtask_added(self):
        # When a task is added to a bug, a new set of headers will be
        # added to the X-Launchpad-Bug headers describing the new task.
        new_bug_task = self.factory.makeBugTask(bug=self.bug)

        notification = BugNotification.selectFirst(orderBy='-id')
        mailer = BugNotificationMailer(notification, 'bug-notification.txt')
        mailer.message_id = '<foobar-example-com>'
        generated_mail = mailer.generateEmail(
            self.bug.owner.preferredemail.email, self.bug.owner)

        expected_headers = self._getExpectedHeaders()
        expected_headers['X-Launchpad-Bug'] = [
            u'product=%s; status=New; '
            u'importance=Undecided; assignee=None;' % (
                self.bug.bugtasks[0].product.name),
            u'product=%s; status=New; '
            u'importance=Undecided; assignee=None;' % (
                self.bug.bugtasks[1].product.name),
            ]
        self.assertEqual(expected_headers, generated_mail.headers)

    def test_marked_as_duplicate(self):
        # When a bug is marked as a duplicate of another bug, its email
        # headers reflect this.
        duplicated_bug = self.factory.makeBug()
        self.bug.markAsDuplicate(duplicated_bug)

        notification = BugNotification.selectFirst(orderBy='-id')
        mailer = BugNotificationMailer(notification, 'bug-notification.txt')
        mailer.message_id = '<foobar-example-com>'
        generated_mail = mailer.generateEmail(
            self.bug.owner.preferredemail.email, self.bug.owner)

        expected_headers = self._getExpectedHeaders(duplicated_bug)
        expected_headers['X-Launchpad-Message-Rationale'] = (
            'Subscriber to Duplicate via Bug %s' % self.bug.id)
        self.assertEqual(expected_headers, generated_mail.headers)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
