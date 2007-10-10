#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Send bug notifications.

This script sends out all the pending bug notifications, and sets
date_emailed to the current date.
"""

__metaclass__ = type

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import IBugNotificationSet
from canonical.launchpad.mail import sendmail
from canonical.launchpad.scripts.bugnotification import get_email_notifications
from canonical.launchpad.scripts.base import LaunchpadCronScript


class SendBugNotifications(LaunchpadCronScript):
    def main(self):
        notifications_sent = False
        pending_notifications = get_email_notifications(getUtility(
            IBugNotificationSet).getNotificationsToSend())
        for bug_notifications, messages in pending_notifications:
            for message in messages:
                self.logger.info("Notifying %s about bug %d." % (
                    message['To'], bug_notifications[0].bug.id))
                sendmail(message)
                self.logger.debug(message.as_string())
            for notification in bug_notifications:
                notification.date_emailed = UTC_NOW
            notifications_sent = True
            # Commit after each batch of email sent, so that we won't
            # re-mail the notifications in case of something going wrong
            # in the middle.
            self.txn.commit()

        if not notifications_sent:
            self.logger.debug("No notifications are pending to be sent.")


if __name__ == '__main__':
    script = SendBugNotifications('send-bug-notifications',
        dbuser=config.malone.bugnotification_dbuser)
    script.lock_and_run()

