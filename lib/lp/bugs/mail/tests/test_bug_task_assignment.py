# Copyright 2010-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for Bug task assignment-related email tests."""

import transaction
from zope.component import getUtility

from lp.bugs.model.bugnotification import BugNotification
from lp.bugs.scripts.bugnotification import construct_email_notifications
from lp.services.mail import stub
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.webapp.snapshot import notify_modified
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestAssignmentNotification(TestCaseWithFactory):
    """Test emails sent when assigned a bug report."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Run the tests as a logged-in user.
        super(TestAssignmentNotification, self).setUp(
            user='test@canonical.com')
        self.user = getUtility(ILaunchBag).user
        self.product = self.factory.makeProduct(owner=self.user,
                                                name='rebirth')
        self.bug = self.factory.makeBug(target=self.product)
        self.bug_task = self.bug.getBugTask(self.product)
        self.person_assigned_email = 'stever@example.com'
        self.person_assigned = self.factory.makePerson(
            name='assigned', displayname='Steve Rogers',
            email=self.person_assigned_email)
        self.team_member_email = 'hankp@example.com'
        self.team_member = self.factory.makePerson(
            name='giantman', displayname='Hank Pym',
            email=self.team_member_email)
        self.team_assigned = self.factory.makeTeam(
            name='avengers', owner=self.user)
        self.team_assigned.addMember(self.team_member, self.user)
        # adding people to a team generates email
        transaction.commit()
        del stub.test_emails[:]

    def test_assignee_notification_message(self):
        """Test notification string when a person is assigned a task by
           someone else."""
        self.assertEqual(len(stub.test_emails), 0, 'emails in queue')
        with notify_modified(self.bug_task, ['assignee'], user=self.user):
            self.bug_task.transitionToAssignee(self.person_assigned)
        transaction.commit()
        self.assertEqual(len(stub.test_emails), 1, 'email not sent')
        rationale = (
            'Sample Person (name12) has assigned this bug to you for Rebirth')
        msg = stub.test_emails[-1][2]
        self.assertTrue(rationale in msg,
                        '%s not in\n%s\n' % (rationale, msg))

    def test_self_assignee_notification_message(self):
        """Test notification string when a person is assigned a task by
           themselves."""
        stub.test_emails = []
        with notify_modified(self.bug_task, ['assignee']):
            self.bug_task.transitionToAssignee(self.user)
        transaction.commit()
        self.assertEqual(1, len(stub.test_emails))
        rationale = (
            'You have assigned this bug to yourself for Rebirth')
        [email] = stub.test_emails
        # Actual message is part 2 of the email.
        msg = email[2]
        self.assertIn(rationale, msg)

    def test_assignee_not_a_subscriber(self):
        """Test that a new recipient being assigned a bug task does send
           a NEW message."""
        self.assertEqual(len(stub.test_emails), 0, 'emails in queue')
        with notify_modified(self.bug_task, ['assignee'], user=self.user):
            self.bug_task.transitionToAssignee(self.person_assigned)
        transaction.commit()
        self.assertEqual(len(stub.test_emails), 1, 'email not sent')
        new_message = '[NEW]'
        msg = stub.test_emails[-1][2]
        self.assertTrue(new_message in msg,
                        '%s not in \n%s\n' % (new_message, msg))

    def test_assignee_new_subscriber(self):
        """Build a list of people who will receive emails about the bug
        task changes and ensure the assignee is not one."""
        with notify_modified(self.bug_task, ['assignee'], user=self.user):
            self.bug_task.transitionToAssignee(self.person_assigned)
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notifications, omitted, messages = construct_email_notifications(
            [latest_notification])
        self.assertEqual(len(notifications), 1,
                         'email notication not created')
        receivers = [message['To'] for message in messages]
        self.assertFalse(self.person_assigned_email in receivers,
            'Assignee was emailed about the bug task change')

    def test_team_assigned_new_subscriber(self):
        """Assign a team, who is not subscribed to a bug, a bug task and
        ensure that team members do not receive an email about the bug
        task changes."""
        with notify_modified(self.bug_task, ['assignee'], user=self.user):
            self.bug_task.transitionToAssignee(self.team_assigned)
        latest_notification = BugNotification.selectFirst(orderBy='-id')
        notifications, omitted, messages = construct_email_notifications(
            [latest_notification])
        self.assertEqual(len(notifications), 1,
                         'email notification not created')
        receivers = [message['To'] for message in messages]
        self.assertFalse(self.team_member_email in receivers,
            'Team member was emailed about the bug task change')
