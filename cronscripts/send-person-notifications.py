#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Send person notifications.

This script sends out all the pending person notifications, and sets
date_emailed to the current date.
"""

__metaclass__ = type

import _pythonpath

from canonical.config import config

from lp.services.scripts.base import LaunchpadCronScript
from lp.registry.scripts.personnotification import PersonNotificationManager


class SendPersonNotifications(LaunchpadCronScript):
    """Send pending notifications to people.

    Pending notifications are stored in the PersonNotification table and have
    a date_emailed == None.

    This script will also delete the notifications that have been retained for
    more than config.person_notification.retained_days days.
    """

    def main(self):
        manager = PersonNotificationManager(self.txn, self.logger)
        unsent_notifications = manager.sendNotifications()
        manager.purgeNotifications(unsent_notifications)


if __name__ == '__main__':
    script = SendPersonNotifications(
        'send-person-notifications', dbuser=config.person_notification.dbuser)
    script.lock_and_run()
