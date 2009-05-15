#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Send person notifications.

This script sends out all the pending person notifications, and sets
date_emailed to the current date.
"""

__metaclass__ = type

import _pythonpath
from datetime import timedelta, datetime
import pytz

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.personnotification import (
    IPersonNotificationSet)
from lp.services.scripts.base import LaunchpadCronScript


class SendPersonNotifications(LaunchpadCronScript):
    """Send pending notifications to people.

    Pending notifications are stored in the PersonNotification table and have
    a date_emailed == None.

    This script will also delete the notifications that have been retained for
    more than config.person_notification.retained_days days.
    """

    def main(self):
        notifications_sent = False
        notification_set = getUtility(IPersonNotificationSet)
        pending_notifications = notification_set.getNotificationsToSend()
        self.logger.info(
            '%d notification(s) to send.' % pending_notifications.count())
        for notification in pending_notifications:
            person = notification.person
            self.logger.info(
                "Sending notification to %s <%s>."
                % (person.name, person.preferredemail.email))
            notification.send()
            notifications_sent = True
            # Commit after each email sent, so that we won't re-mail the
            # notifications in case of something going wrong in the middle.
            self.txn.commit()

        if not notifications_sent:
            self.logger.debug("No notifications were sent.")

        # Delete PersonNotifications that are older than the retention
        # limit set in the configuration.
        retained_days = timedelta(
            days=int(config.person_notification.retained_days))
        time_limit = (datetime.now(pytz.timezone('UTC')) - retained_days)
        to_delete = notification_set.getNotificationsOlderThan(time_limit)
        if to_delete.count():
            self.logger.info(
                "Notification retention limit is %s." % retained_days)
            self.logger.info(
                "Deleting %d old notification(s)." % to_delete.count())
            for notification in to_delete:
                notification.destroySelf()
            self.txn.commit()


if __name__ == '__main__':
    script = SendPersonNotifications(
        'send-person-notifications', dbuser=config.person_notification.dbuser)
    script.lock_and_run()
