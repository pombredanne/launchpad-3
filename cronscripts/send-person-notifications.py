#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Send person notifications.

This script sends out all the pending person notifications, and sets
date_emailed to the current date.
"""

__metaclass__ = type

import _pythonpath
from datetime import timedelta, datetime
import pytz

from email.MIMEText import MIMEText

from zope.component import getUtility

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import IPersonNotificationSet
from canonical.launchpad.mail import sendmail
from canonical.launchpad.mailnotification import format_rfc2822_date
from canonical.launchpad.scripts.base import LaunchpadCronScript


def construct_email(notification):
    """Constructs a MIMEText message based on a person notification."""
    msg = MIMEText(notification.body.encode('utf8'), 'plain', 'utf8')
    msg['From'] = config.canonical.bounce_address
    msg['To'] = notification.person.preferredemail.email
    msg['Sender'] = config.canonical.bounce_address
    msg['Date'] = format_rfc2822_date(notification.date_created)
    msg['Subject'] = notification.subject

    return msg


class SendPersonNotifications(LaunchpadCronScript):
    def main(self):
        notifications_sent = False
        notification_set = getUtility(IPersonNotificationSet)
        pending_notifications = notification_set.getNotificationsToSend()
        self.logger.info('%d notification(s) to send.' %
                    pending_notifications.count())
        for notification in pending_notifications:
            if notification.person.preferredemail is None:
                self.logger.info('No email address for %s' % (
                    notification.person.name))
                continue
            message = construct_email(notification)
            self.logger.info("Sending notice to %s: %s." % (
                notification.person.name, message['To']))
            sendmail(message)
            self.logger.debug(message.as_string())
            notification.date_emailed = UTC_NOW
            notifications_sent = True
            # Commit after each email sent, so that we won't re-mail the
            # notifications in case of something going wrong in the middle.
            self.txn.commit()

        if not notifications_sent:
            self.logger.debug("No notifications are pending to be sent.")

        # Delete PersonNotification's that are older than the retention
        # limit set in the configuration.
        retained_days = timedelta(
            days=int(config.person_notification.retained_days))
        time_limit = (datetime.now(pytz.timezone('UTC')) - retained_days)
        to_delete = notification_set.olderThan(time_limit)
        if to_delete.count():
            self.logger.info(
                "Notification retention limit is %s." % retained_days)
            self.logger.info(
                "Deleting %d old notification(s)." % to_delete.count())
        for notification in to_delete:
            notification.destroySelf()
        self.txn.commit()


if __name__ == '__main__':
    script = SendPersonNotifications('send-person-notifications',
        dbuser=config.person_notification.dbuser)
    script.lock_and_run()

