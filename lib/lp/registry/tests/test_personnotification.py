# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the PersonNotification classes."""

__metaclass__ = type


from datetime import (
    datetime,
    timedelta,
    )
import logging

import pytz
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.testing import (
    DatabaseFunctionalLayer,
    reset_logging,
    )
from lp.registry.interfaces.personnotification import IPersonNotificationSet
from lp.registry.scripts.personnotification import PersonNotificationManager
from lp.testing import TestCaseWithFactory


class TestPersonNotificationManager(TestCaseWithFactory):
    """Tests for the PersonNotificationManager use in scripts."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonNotificationManager, self).setUp()
        logging.basicConfig(level=logging.CRITICAL)
        logger = logging.getLogger()
        self.manager = PersonNotificationManager(transaction, logger)
        self.notification_set = getUtility(IPersonNotificationSet)

    def tearDown(self):
        super(TestPersonNotificationManager, self).tearDown()
        reset_logging()

    def test_sendNotifications_sent(self):
        user = self.factory.makePerson()
        notification = self.notification_set.addNotification(
            user, 'subject', 'body')
        unsent = self.manager.sendNotifications()
        self.assertEqual(None, unsent)
        self.failIf(notification.date_emailed is None)

    def test_sendNotifications_unsent(self):
        user = self.factory.makePerson()
        notification = self.notification_set.addNotification(
            user, 'subject', 'body')
        user.setPreferredEmail(None)
        unsent = self.manager.sendNotifications()
        self.assertEqual([notification], unsent)
        self.assertEqual(None, notification.date_emailed)

    def test_purgeNotifications_old(self):
        user = self.factory.makePerson()
        notification = self.notification_set.addNotification(
            user, 'subject', 'body')
        age = timedelta(
            days=int(config.person_notification.retained_days) + 1)
        naked_notification = removeSecurityProxy(notification)
        naked_notification.date_created = (
            datetime.now(pytz.timezone('UTC')) - age)
        self.manager.purgeNotifications()
        notifcations = self.notification_set.getNotificationsToSend()
        self.assertEqual(0, notifcations.count())

    def test_purgeNotifications_extra(self):
        user = self.factory.makePerson()
        notification = self.notification_set.addNotification(
            user, 'subject', 'body')
        user.setPreferredEmail(None)
        self.manager.purgeNotifications(extra_notifications=[notification])
        notifcations = self.notification_set.getNotificationsToSend()
        self.assertEqual(0, notifcations.count())
