# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test notification classes and functions."""

__metaclass__ = type

from lp.registry.mail.notification import send_direct_contact_email
from lp.services.mail.notificationrecipientset import NotificationRecipientSet
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.mail_helpers import pop_notifications


class SendDirectContactEmailTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_send_success(self):
        sender = self.factory.makePerson(email='me@eg.dom', name='me')
        user = self.factory.makePerson(email='him@eg.dom', name='him')
        subject = 'test subject'
        body = 'test body'
        recipients_set = NotificationRecipientSet()
        recipients_set.add(user, 'test reason', 'test rationale')
        pop_notifications()
        send_direct_contact_email('me@eg.dom', recipients_set, subject, body)
        notifications = pop_notifications()
        notification = notifications[0]
        self.assertEqual(1, len(notifications))
        self.assertEqual('Me <me@eg.dom>', notification['From'])
        self.assertEqual('Him <him@eg.dom>', notification['To'])
        self.assertEqual(subject, notification['Subject'])
        self.assertEqual(
            'test rationale', notification['X-Launchpad-Message-Rationale'])
        self.assertTrue('launchpad' in notification['Message-ID'])
