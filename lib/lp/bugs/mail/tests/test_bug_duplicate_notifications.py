# Copyright 2010-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for notification strings of duplicate Bugs."""

import transaction
from zope.component import getUtility

from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.model.bugnotification import BugNotification
from lp.bugs.scripts.bugnotification import construct_email_notifications
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.webapp.snapshot import notify_modified
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestAssignmentNotification(TestCaseWithFactory):
    """Test emails sent when a bug is a duplicate of another."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Run the tests as a logged-in user.
        super(TestAssignmentNotification, self).setUp(
            user='test@canonical.com')
        self.user = getUtility(ILaunchBag).user
        self.product = self.factory.makeProduct(owner=self.user,
                                                name='project')
        self.master_bug = self.factory.makeBug(target=self.product)
        self.dup_bug = self.factory.makeBug(target=self.product)
        self.master_bug_task = self.master_bug.getBugTask(self.product)
        self.person_subscribed_email = 'person@example.com'
        self.person_subscribed = self.factory.makePerson(
            name='subscribed', displayname='Person',
            email=self.person_subscribed_email)
        self.dup_bug.subscribe(
            self.person_subscribed, subscribed_by=self.user)
        self.dup_bug.markAsDuplicate(self.master_bug)
        self.master_bug.clearBugNotificationRecipientsCache()

    def test_dup_subscriber_change_notification_message(self):
        """Duplicate bug number in the reason (email footer) for
           duplicate subscribers when a master bug is modified."""
        with notify_modified(self.master_bug_task, ['status'], user=self.user):
            self.master_bug_task.transitionToStatus(
                BugTaskStatus.CONFIRMED, self.user)
        transaction.commit()
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notifications, omitted, messages = construct_email_notifications(
            [latest_notification])
        self.assertEqual(
            len(notifications), 1, 'email notification not created')
        rationale = 'duplicate bug report (%i)' % self.dup_bug.id
        self.assertIn(rationale, str(messages[-1]))
