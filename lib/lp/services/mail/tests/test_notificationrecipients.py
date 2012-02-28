# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.registry.interfaces.person import PersonVisibility
from lp.services.mail.notificationrecipientset import NotificationRecipientSet
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer

class TestNotificationRecipientSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_add_doesnt_break_on_private_teams(self):
        # Since notifications are not exposed to UI, they should handle
        # protected preferred emails fine.
        email = self.factory.getUniqueEmailAddress()
        notified_team = self.factory.makeTeam(
            email=email, visibility=PersonVisibility.PRIVATE)
        recipients = NotificationRecipientSet()
        notifier = self.factory.makePerson()
        with person_logged_in(notifier):
            recipients.add([notified_team], 'some reason', 'some header')
        self.assertEqual([notified_team], recipients.getRecipients())
